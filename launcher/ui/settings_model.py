# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Settings screen's model (context property `settings`): the rows of each tab for the game being edited,
Quick setup's presets, and the key / mouse binding capture. Every change goes to core.settings, which saves it at
once; errors become a message for the player (`notice`)."""
from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core import config as cfg
from core import controls, games, gpu, input_map, presets, resolution, settings

CAPTURE_SECONDS = 6
SCOPE_KEY = "controls_scope"  # the Controls tab's top row: whose keys it shows
CHEATS_NOTE = "Applied when a game starts. Made for update 1.02 of the game."
CREDITS = ("DLSS and DLAA use NVIDIA DLSS technology; NVIDIA, RTX and DLSS are trademarks of NVIDIA Corporation. "
           "FSR 3.1 and FSR 4 are AMD FidelityFX Super Resolution.")
CAPTURE_HINT = ("Click a slot (or Enter), then press a key, a mouse button or turn the wheel. Right-click a slot to "
                "clear it. In the game Left Alt frees the mouse and Insert opens the menu.")

# How each tab is laid out beyond its settings: ("section", title), ("button", title, hint, action, argument,
# label), ("note", text) or a setting's key.
ADVANCED_LAYOUT: tuple[Any, ...] = (
    ("section", "YOUR GAME"), "save_profile", "language",
    ("section", "PICTURE"), "anisotropy", "no_dof",
    ("section", "CONTROLS"), "menu_shortcut",
    ("section", "LAUNCHER"), "check_updates", "diagnostics",
    ("button", "Check for updates", "Looks for a newer El Dorado release now.", "checkForUpdates", "", "CHECK"),
    ("section", "SHORTCUTS"),
    ("button", "Desktop shortcuts", "El Dorado and one shortcut per game on the desktop.", "createShortcuts", "",
     "CREATE"),
    ("button", "Add to Steam", "The Collection as one non-Steam game in your library.", "addToSteam", "collection",
     "ADD"),
    ("button", "Add the three games to Steam", "One non-Steam game per Uncharted, each starting its game "
     "directly.", "addToSteam", "games", "ADD"),
    ("section", "GAME FILES"),
    ("button", "Game folder", "The folder with eboot.bin and sce_sys.", "chooseGameFolder", "", "CHANGE"),
    ("button", "Install game from .pkg", "Your own game package unpacked into a folder you choose (about 60 GB); "
     "it becomes the game folder.", "installGamePkg", "", "INSTALL"),
    ("button", "Check game files", "Looks for missing or damaged game files.", "checkGameFiles", "", "CHECK"),
    ("button", "Game update folder", "Your extracted update 1.02 folder, wherever it is.", "chooseUpdateFolder", "",
     "CHOOSE"),
    ("button", "Install game update", "From the update's .pkg file (also a translation's).", "installUpdatePkg", "",
     "INSTALL"),
    ("button", "Log folder", "", "openFolder", "logs", "OPEN"),
    ("button", "Save folder", "", "openFolder", "saves", "OPEN"),
    ("button", "Screenshot folder", "", "openFolder", "screenshots", "OPEN"),
    ("section", "TROUBLESHOOTING"),
    ("button", "Clear shader cache", "The shaders are prepared again at the next start.", "clearShaderCache", "",
     "CLEAR"),
    ("button", "Reset all settings", "Back to the Medium preset and the default controls.", "resetSettings", "",
     "RESET"),
)

# Windows' scan codes of the main block's letters and digits: a binding names the key's place, whatever the
# keyboard layout prints on it (an Arabic layout's letters would otherwise reach the game).
_SCANCODE_NAMES: dict[int, str] = {
    **{code: name for code, name in zip(range(2, 12), "1234567890")},
    **{code: name for code, name in zip(range(16, 26), "QWERTYUIOP")},
    **{code: name for code, name in zip(range(30, 39), "ASDFGHJKL")},
    **{code: name for code, name in zip(range(44, 51), "ZXCVBNM")},
    42: "Left Shift", 54: "Right Shift", 29: "Left Ctrl", 285: "Right Ctrl", 56: "Left Alt", 312: "Right Alt",
}
_K = Qt.Key
_KEY_NAMES: dict[int, str] = {key.value: name for key, name in (
    (_K.Key_Space, "Space"), (_K.Key_Return, "Return"), (_K.Key_Escape, "Escape"), (_K.Key_Tab, "Tab"),
    (_K.Key_Backspace, "Backspace"), (_K.Key_CapsLock, "CapsLock"), (_K.Key_Up, "Up"), (_K.Key_Down, "Down"),
    (_K.Key_Left, "Left"), (_K.Key_Right, "Right"), (_K.Key_Delete, "Delete"), (_K.Key_Home, "Home"),
    (_K.Key_End, "End"), (_K.Key_PageUp, "PageUp"), (_K.Key_PageDown, "PageDown"), (_K.Key_Insert, "Insert"),
    (_K.Key_Pause, "Pause"), (_K.Key_ScrollLock, "ScrollLock"), (_K.Key_Minus, "-"), (_K.Key_Equal, "="),
    (_K.Key_BracketLeft, "["), (_K.Key_BracketRight, "]"), (_K.Key_Backslash, "\\"), (_K.Key_Semicolon, ";"),
    (_K.Key_Apostrophe, "'"), (_K.Key_QuoteLeft, "`"), (_K.Key_Period, "."), (_K.Key_Slash, "/"),
    (_K.Key_Shift, "Left Shift"), (_K.Key_Control, "Left Ctrl"), (_K.Key_Alt, "Left Alt"),
    *((getattr(_K, f"Key_F{n}"), f"F{n}") for n in range(1, 13)),
)}
_KEYPAD_NAMES: dict[int, str] = {key.value: name for key, name in (
    (_K.Key_Slash, "Keypad /"), (_K.Key_Asterisk, "Keypad *"), (_K.Key_Minus, "Keypad -"), (_K.Key_Plus, "Keypad +"),
    (_K.Key_Enter, "Keypad Enter"), (_K.Key_Return, "Keypad Enter"), (_K.Key_Period, "Keypad ."),
    *((getattr(_K, f"Key_{n}"), f"Keypad {n}") for n in range(10)),
)}
_KEYPAD = Qt.KeyboardModifier.KeypadModifier.value


def sdl_key_name(key: int, scancode: int, modifiers: int) -> str | None:
    """The SDL name of a pressed key (Qt's key code, Windows' scan code), None for a key the game cannot use."""
    if modifiers & _KEYPAD:
        return _KEYPAD_NAMES.get(key)
    if scancode in _SCANCODE_NAMES:
        return _SCANCODE_NAMES[scancode]
    if _K.Key_A.value <= key <= _K.Key_Z.value or _K.Key_0.value <= key <= _K.Key_9.value:
        return chr(key)
    return _KEY_NAMES.get(key)


def _options(pairs: settings.Options) -> list[dict[str, str]]:
    return [{"value": value, "label": label} for value, label in pairs]


class SettingsModel(QObject):
    changed = Signal()
    notice = Signal(str)
    _detected = Signal(object)
    _arabic_found = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        config = cfg.Config.load()
        known = str(config.data.get("gpu") or "")
        # Arabic is offered once the background check has found which games have it ({} until then).
        self._editor = settings.Editor(card=gpu.Gpu(known) if known else None, arabic={})
        self._game = config.selected
        # The Controls tab's scope: ALL GAMES, or one game (its own items on top of the shared set).
        self._scope = controls.ALL
        self._capture: tuple[str, int] | None = None
        self._hint = CAPTURE_HINT
        self._reset_armed = False
        self._arabic_source: tuple[str, str] | None = None
        for key in games.KEYS:
            self._sync(key)
        self._capture_timer = QTimer(self)
        self._capture_timer.setSingleShot(True)
        self._capture_timer.setInterval(CAPTURE_SECONDS * 1000)
        self._capture_timer.timeout.connect(self.cancelCapture)
        self._detected.connect(self._on_detected)
        self._arabic_found.connect(self._on_arabic_found)
        threading.Thread(target=lambda: self._detected.emit(gpu.detect()), daemon=True).start()
        self._check_arabic(config)

    # --- what QML reads ---------------------------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def games(self) -> list[dict[str, str]]:
        return [{"key": game.key, "name": game.name, "short": f"UNCHARTED {game.number}"} for game in games.GAMES]

    @Property(int, notify=changed)
    def gameIndex(self) -> int:
        return games.KEYS.index(self._game)

    @Property(str, notify=changed)
    def gameName(self) -> str:
        return games.by_key(self._game).name

    @Property(str, notify=changed)
    def controlsScope(self) -> str:
        return self._scope

    @Property(str, notify=changed)
    def controlsScopeName(self) -> str:
        return "All games" if self._scope == controls.ALL else games.by_key(self._scope).name

    @Property("QVariantList", constant=True)
    def tabs(self) -> list[dict[str, str]]:
        return [{"key": key, "title": title} for key, title in settings.TABS]

    @Property("QVariantMap", notify=changed)
    def pages(self) -> dict[str, list[dict[str, Any]]]:
        config = self._editor.load()
        values = self._editor.values(self._game, config)
        return {"display": self._display_rows(config, values),
                "performance": self._performance_rows(config, values),
                "controls": self._controls_rows(config, values),
                "cheats": [{"kind": "note", "text": CHEATS_NOTE}] + self._setting_rows("cheats", config, values),
                "advanced": self._advanced_rows(config, values)}

    @Property("QVariantList", notify=changed)
    def presets(self) -> list[dict[str, Any]]:
        chosen = self._editor.load().game(self._game).get("preset")
        return [{"name": preset.name, "title": preset.title, "summary": preset.summary, "detail": preset.detail,
                 "selected": preset.name == chosen, "yourPc": preset.name == "recommended"}
                for preset in self._editor.preset_list()]

    @Property(str, notify=changed)
    def setupNote(self) -> str:
        card = self._editor.card
        intro = (f"Your graphics card: {card.name}. RECOMMENDED is made for it; " if card else "Pick a quality level; ")
        custom = self._editor.load().game(self._game).get("preset") not in presets.ORDER
        game = self.gameName
        per_game = f"{game}: custom settings (changed by hand)." if custom else \
            f"Settings are kept per game: these are {game}'s."
        return intro + "every setting can still be changed in Display and Performance.\n" + per_game

    @Property(str, notify=changed)
    def capturing(self) -> str:
        return f"{self._capture[0]}:{self._capture[1]}" if self._capture else ""

    @Property(bool, notify=changed)
    def resetArmed(self) -> bool:
        return self._reset_armed

    # --- what QML calls ---------------------------------------------------------------------------------------

    @Slot(int)
    def selectGame(self, index: int) -> None:
        if 0 <= index < len(games.KEYS) and games.KEYS[index] != self._game:
            self._capture = None
            self._reset_armed = False
            self._game = games.KEYS[index]
            self._sync(self._game)
            self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        """The files changed outside this screen (a game folder or update chosen, a .pkg installed, a reset):
        every tab reads them again, and the Arabic translation is looked for in the new folders."""
        self.changed.emit()

    @Slot(str)
    def setControlsScope(self, scope: str) -> None:
        """The Controls tab shows and changes ALL GAMES, or one game."""
        if scope != controls.ALL:
            games.by_key(scope)
        self._capture = None
        self._reset_armed = False
        self._scope = scope
        self.changed.emit()

    @Slot(str)
    def clearOwn(self, action: str) -> None:
        """A game's own keys and controller button of one action back to ALL GAMES."""
        self._do(lambda: [self._editor.clear_own(self._scope, controls.Item(kind, action))
                          for kind in ("binding", "pad")])

    @Slot(str)
    def clearOwnSetting(self, name: str) -> None:
        self._do(lambda: self._editor.clear_own(self._scope, controls.Item("setting", name)))

    @Slot()
    def dropOwn(self) -> None:
        """The game follows ALL GAMES again in everything."""
        self._do(lambda: self._editor.clear_own(self._scope))

    @Slot()
    def makeShared(self) -> None:
        """The game's keys and settings become the ALL GAMES ones."""
        self._do(lambda: self._editor.make_shared(self._scope))

    @Slot(str, "QVariant")
    def set(self, name: str, value: Any) -> None:
        if name == SCOPE_KEY:
            self.setControlsScope(str(value))
        elif name in controls.SETTING_NAMES:
            self._do(lambda: self._editor.set_control(self._scope, name, value))
        else:
            self._do(lambda: self._editor.set(self._game, name, value))

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        self._do(lambda: self._editor.apply_preset(self._game, name))

    @Slot(str, int)
    def startCapture(self, action: str, slot: int) -> None:
        self._capture = (action, slot)
        self._hint = "Press a key or a mouse button, or turn the wheel."
        self._capture_timer.start()
        self.changed.emit()

    @Slot()
    def cancelCapture(self) -> None:
        if self._capture:
            self._capture = None
            self._hint = CAPTURE_HINT
            self.changed.emit()

    @Slot(int, int, int)
    def captureKey(self, key: int, scancode: int, modifiers: int) -> None:
        if not self._capture:
            return
        name = sdl_key_name(key, scancode, modifiers)
        if name in input_map.RESERVED_KEYS:
            self._end_capture(f"{name} belongs to the game window (Insert: the menu, Left Alt: frees the mouse). "
                              "Choose another key.")
        elif not name:
            self._end_capture("That key can't be used in the game. Choose another key.")
        else:
            self._bind("key:" + name)

    @Slot(str)
    def captureMouse(self, button: str) -> None:
        if self._capture and button in input_map.MOUSE_BUTTONS:
            self._bind("mouse:" + button)

    @Slot(str, int)
    def clearBinding(self, action: str, slot: int) -> None:
        self._capture = None
        self._do(lambda: self._editor.bind(self._scope, action, slot, None))

    @Slot(str, str)
    def setPad(self, action: str, button: str) -> None:
        self._do(lambda: self._editor.bind_pad(self._scope, action, button or None))

    @Slot()
    def resetControls(self) -> None:
        """The first press arms it, the second puts the ALL GAMES controls back to the defaults."""
        if not self._reset_armed:
            self._reset_armed = True
            self.changed.emit()
            return
        self._reset_armed = False
        self._do(lambda: self._editor.reset_controls(self._scope))

    # --- inside ---------------------------------------------------------------------------------------------------

    def _do(self, change: Any) -> None:
        try:
            change()
        except (ValueError, KeyError, OSError) as error:
            self.notice.emit(f"Not saved: {error}")
        self.changed.emit()

    def _sync(self, key: str) -> None:
        try:
            self._editor.sync_controls(key)
        except OSError as error:
            self.notice.emit(f"Could not read {games.by_key(key).name}'s controls: {error}")

    def _bind(self, binding: str) -> None:
        assert self._capture is not None
        action, slot = self._capture
        self._capture = None
        self._capture_timer.stop()
        try:
            self._editor.bind(self._scope, action, slot, binding)
            where = "all games" if self._scope == controls.ALL else self.controlsScopeName
            self._hint = f"Saved for {where}. " + CAPTURE_HINT
        except (ValueError, OSError) as error:
            self._hint = str(error)
        self.changed.emit()

    def _end_capture(self, hint: str) -> None:
        self._capture = None
        self._capture_timer.stop()
        self._hint = hint
        self.changed.emit()

    def _on_detected(self, card: gpu.Gpu | None) -> None:
        if card is None:
            return
        try:
            self._editor.remember_card(card)
            self._apply_pending_recommended()
        except OSError as error:
            self.notice.emit(f"Could not save the settings: {error}")
        self.changed.emit()

    def _check_arabic(self, config: cfg.Config) -> None:
        """Which games have the Arabic translation, found off the UI thread (the first look reads each game's text
        archive); looked for again when the game folder or the update changes."""
        source = (str(config.data.get("game_dir") or ""), str(config.data.get("update_dir") or ""))
        if source == self._arabic_source:
            return
        self._arabic_source = source
        threading.Thread(target=lambda: self._arabic_found.emit((source, settings.arabic_available(config))),
                         daemon=True).start()

    def _on_arabic_found(self, packet: tuple[tuple[str, str], dict[str, bool]]) -> None:
        source, found = packet
        if source != self._arabic_source:
            return  # the folders changed again while this look ran; the newer look answers
        self._editor.arabic = found
        self.changed.emit()

    def _apply_pending_recommended(self) -> None:
        """The first start asked for Recommended in every game; it is applied once the graphics card is known."""
        config = self._editor.load()
        if not config.data.get("recommended_pending"):
            return
        for key in games.KEYS:
            self._editor.apply_preset(key, "recommended")
        config = self._editor.load()
        config.data.pop("recommended_pending", None)
        config.save()

    # --- rows ----------------------------------------------------------------------------------------------------

    def _row(self, name: str, config: cfg.Config, values: dict[str, Any], enabled: bool = True) -> dict[str, Any]:
        setting = settings.BY_KEY[name]
        row: dict[str, Any] = {"key": name, "title": setting.title, "hint": setting.hint, "enabled": enabled}
        if setting.toggle:
            row.update(kind="toggle", checked=bool(values[name]))
        else:
            row.update(kind="choice", value=str(values[name]),
                       options=_options(self._editor.options(self._game, name, config)))
        return row

    def _setting_rows(self, tab: str, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        return [self._row(setting.key, config, values) for setting in settings.in_tab(tab)]

    def _display_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        render, output = self._editor.sizes(self._game, config)
        upscaling = values["upscaling"]
        temporal = upscaling in resolution.TEMPORAL_UPSCALERS
        rows = []
        for setting in settings.in_tab("display"):
            name = setting.key
            if name == "upscale" and upscaling == "off":
                continue
            enabled = not (name == "aa" and temporal) and \
                not (name.startswith("overlay_") and not values["show_fps"])
            rows.append(self._row(name, config, values, enabled))
            if name == "resolution" and not output:
                rows.append({"kind": "note", "text": "Render size: " + render.replace("x", " × ")})
            if name == "upscale" and output:
                rows.append({"kind": "note", "text": f"Draws {render.replace('x', ' × ')}, upscaled to "
                                                     f"{output.replace('x', ' × ')}"})
        return rows

    def _performance_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._setting_rows("performance", config, values)
        screen = QGuiApplication.primaryScreen()
        hz = round(screen.refreshRate()) if screen else 60
        note = f"With VSync your monitor's refresh rate ({hz} Hz) is the smoothest limit."
        if int(values["fps_limit"]) > 60:
            note = f"Frame rate unlocked up to {values['fps_limit']} FPS (your monitor: {hz} Hz). " + note
        rows.insert(1, {"kind": "note", "text": note})
        return rows

    def _controls_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        """One choice at the top says whose keys the tab shows (ALL GAMES, or one game); a game that has keys of
        its own gets one button to take the ALL GAMES keys again. Then the settings and the bindings."""
        scope = self._scope
        scope_options = [{"value": controls.ALL, "label": "All games"}] + [
            {"value": game.key, "label": f"Uncharted {game.number} only"} for game in games.GAMES]
        rows: list[dict[str, Any]] = [{"kind": "choice", "key": SCOPE_KEY, "title": "These keys are for",
                                       "hint": "", "enabled": True, "value": scope, "options": scope_options}]
        if scope != controls.ALL and controls.own_items(config, scope):
            rows.append({"kind": "button", "title": f"{self.controlsScopeName} has keys of its own",
                         "hint": "The other games use the ALL GAMES keys.", "action": "useAllGamesKeys", "arg": "",
                         "label": "USE THE ALL GAMES KEYS", "danger": False})
        scope_values = {**values, **self._editor.control_values(scope, config)}
        for setting in settings.in_tab("controls"):
            row = self._row(setting.key, config, scope_values)
            if row["kind"] == "choice":
                row["options"] = _options(self._editor.control_options(scope, setting.key, config))
            rows.append(row)
        if scope == controls.ALL:
            rows.append({"kind": "button", "title": "Reset controls",
                         "hint": "Every key, button and setting back to the defaults.",
                         "action": "resetControls", "arg": "",
                         "label": "PRESS AGAIN" if self._reset_armed else "RESET", "danger": self._reset_armed})
        rows.append({"kind": "note", "text": self._hint})
        current = controls.control_set(config, scope)
        style = str(scope_values["prompts"])
        pad_options = [{"value": "", "label": "—"}] + [
            {"value": button, "label": input_map.pad_label(button, style)} for button in input_map.PAD_BUTTONS]
        for title, actions in input_map.GROUPS:
            rows.append({"kind": "section", "title": title})
            for action, label in actions:
                bound = current.bindings[action]
                fixed = action not in input_map.PAD_DEFAULTS
                button = input_map.PAD_FIXED.get(action) if fixed else current.pad.get(action)
                rows.append({"kind": "binding", "action": action, "title": label,
                             "keys": [input_map.label(bound[slot] if slot < len(bound) else None)
                                      for slot in range(input_map.SLOTS)],
                             "capture": [self._capture == (action, slot) for slot in range(input_map.SLOTS)],
                             "pad": input_map.pad_label(button, style, action), "padValue": button or "",
                             "padFixed": fixed, "padOptions": pad_options})
        return rows

    def _advanced_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        self._check_arabic(config)  # a game folder or update chosen since the last look
        rows: list[dict[str, Any]] = []
        for item in ADVANCED_LAYOUT:
            if isinstance(item, str):
                rows.append(self._row(item, config, values))
            elif item[0] == "section":
                rows.append({"kind": "section", "title": item[1]})
            else:
                _, title, hint, action, argument, label = item
                rows.append({"kind": "button", "title": title, "hint": hint, "action": action, "arg": argument,
                             "label": label, "danger": action == "resetSettings"})
        update = config.chosen_update()
        rows.append({"kind": "note", "text": f"Game files: {config.game_dir()}\n"
                                             f"Game update: {update or 'next to the game folder, if there is one'}\n"
                                             f"Settings: {cfg.ini_file(self._game)}"})
        rows.append({"kind": "note", "text": CREDITS})
        return rows
