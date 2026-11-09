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
from core import controls, game_files, games, gpu, i18n, input_map, presets, resolution, settings
from core.i18n import t

CAPTURE_SECONDS = 6
SCOPE_KEY = "controls_scope"  # the Controls tab's top row: whose keys it shows
U2_HIGH_FPS = ("Uncharted 2 above 60 FPS: players report Nate passing through the second blade in The Path of Light "
               "and crashes in chapter 21 (Convoy). Play those at 60.")
CHEATS_NOTE = "For all three games, applied when a game starts. Made for update 1.02 of the game."
CREDITS = ("DLSS and DLAA use NVIDIA DLSS technology; NVIDIA, RTX and DLSS are trademarks of NVIDIA Corporation. "
           "FSR 3.1 and FSR 4 are AMD FidelityFX Super Resolution.")
CAPTURE_HINT = ("Click a slot (or Enter), then press a key, a mouse button or turn the wheel. Right-click a slot to "
                "clear it. In the game Left Alt frees the mouse and Insert opens the menu.")

# How each tab is laid out beyond its settings: ("section", title), ("button", title, hint, action, argument,
# label), ("note", text) or a setting's key. The texts are English here and translated where the rows are built.
FILES_LAYOUT: tuple[Any, ...] = (
    ("section", "GAME FOLDER"),
    ("button", "Game folder", "The folder with eboot.bin and sce_sys.", "chooseGameFolder", "", "CHANGE"),
    ("button", "Install game from .pkg", "Your own game package unpacked into a folder you choose (about 60 GB); "
     "it becomes the game folder.", "installGamePkg", "", "INSTALL"),
    ("button", "Check game files", "Looks for missing or damaged game files.", "checkGameFiles", "", "CHECK"),
    ("section", "GAME UPDATE"),
    ("button", "Install game update", "From the update's .pkg file (also a translation's).", "installUpdatePkg", "",
     "INSTALL"),
    ("section", "TROUBLESHOOTING"),
    ("button", "Prepare shaders", "Prepares the three games' shaders now (a few minutes), so each game opens "
     "straight away the first time.", "prepareShaders", "", "PREPARE"),
    ("button", "Clear shader cache", "The shaders are prepared again at the next start.", "clearShaderCache", "",
     "CLEAR"),
)
LAUNCHER_LAYOUT: tuple[Any, ...] = (
    ("section", "UPDATES"), "check_updates",
    ("button", "Check for updates", "Looks for a newer El Dorado release now.", "checkForUpdates", "", "CHECK"),
    ("section", "SHORTCUTS"),
    ("button", "Desktop shortcuts", "El Dorado and one shortcut per game on the desktop.", "createShortcuts", "",
     "CREATE"),
    ("button", "Add to Steam", "The Collection as one non-Steam game in your library.", "addToSteam", "collection",
     "ADD"),
    ("button", "Add the three games to Steam", "One non-Steam game per Uncharted, each starting its game "
     "directly.", "addToSteam", "games", "ADD"),
    ("section", "FOLDERS"),
    ("button", "Log folder", "", "openFolder", "logs", "OPEN"),
    ("button", "Save folder", "", "openFolder", "saves", "OPEN"),
    ("button", "Screenshot folder", "", "openFolder", "screenshots", "OPEN"),
    ("section", "TROUBLESHOOTING"), "diagnostics",
    ("button", "Problem report", "The logs and settings in one zip on your Desktop, to attach to a report.",
     "problemReport", "", "CREATE"),
    ("button", "Reset all settings", "Back to the Medium preset and the default controls.", "resetSettings", "",
     "RESET"),
)
# Settings each game has on its own row in a tab for all games (Language, Game files): "<setting>:<game key>".
PER_GAME_ROW = ":"

# Windows' scan codes of the main block's letters and digits: a binding names the key's place, whatever the
# keyboard layout prints on it (an Arabic layout's letters would otherwise reach the game).
_SCANCODE_NAMES: dict[int, str] = {
    **{code: name for code, name in zip(range(2, 12), "1234567890")},
    **{code: name for code, name in zip(range(16, 26), "QWERTYUIOP")},
    **{code: name for code, name in zip(range(30, 39), "ASDFGHJKL")},
    **{code: name for code, name in zip(range(44, 51), "ZXCVBNM")},
    42: "Left Shift", 54: "Right Shift", 29: "Left Ctrl", 285: "Right Ctrl", 56: "Left Alt", 312: "Right Alt",
    # The punctuation keys by their place too (another layout prints other characters on them).
    12: "-", 13: "=", 26: "[", 27: "]", 43: "\\", 39: ";", 40: "'", 41: "`", 51: ",", 52: ".", 53: "/",
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


def _options(pairs: settings.Options, translate: bool = True) -> list[dict[str, str]]:
    """A choice's options for QML; their labels in the launcher's language unless already final (the game
    languages are named in their own language)."""
    return [{"value": value, "label": t(label) if translate else label} for value, label in pairs]


def _send(signal: Signal, value: object) -> None:
    """A background look's answer; the window may have closed meanwhile (its objects are gone, nothing to tell)."""
    try:
        signal.emit(value)
    except RuntimeError:
        pass


class SettingsModel(QObject):
    changed = Signal()
    notice = Signal(str)
    # The launcher's own language chosen in Advanced (main.py hands it to the language model, which saves it).
    languageWanted = Signal(str)
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
        self._hint = ""  # "" = CAPTURE_HINT, read in the launcher's language when shown
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
        threading.Thread(target=lambda: _send(self._detected, gpu.detect()), daemon=True).start()
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
        return t("All games") if self._scope == controls.ALL else games.by_key(self._scope).name

    @Property("QVariantList", notify=changed)
    def tabs(self) -> list[dict[str, str]]:
        return [{"key": key, "title": t(title)} for key, title in settings.TABS]

    @Property("QVariantMap", notify=changed)
    def pages(self) -> dict[str, list[dict[str, Any]]]:
        config = self._editor.load()
        values = self._editor.values(self._game, config)
        return {"display": self._display_rows(config, values),
                "performance": self._performance_rows(config, values),
                "controls": self._controls_rows(config, values),
                "cheats": [{"kind": "note", "text": t(CHEATS_NOTE)}] + self._setting_rows("cheats", config, values),
                "language": self._language_rows(config),
                "files": [self._game_info(config)] + self._layout_rows(FILES_LAYOUT, config, values),
                "launcher": self._layout_rows(LAUNCHER_LAYOUT, config, values) + [{"kind": "note", "text": t(CREDITS)}]}

    @Property("QVariantList", notify=changed)
    def presets(self) -> list[dict[str, Any]]:
        chosen = self._editor.load().game(self._game).get("preset")
        return [{"name": preset.name, "title": t(preset.title), "summary": t(preset.summary),
                 "detail": t(preset.detail),
                 "selected": preset.name == chosen, "yourPc": preset.name == "recommended"}
                for preset in self._editor.preset_list()]

    @Property(str, notify=changed)
    def setupNote(self) -> str:
        card = self._editor.card
        intro = (t("Your graphics card: {card}. RECOMMENDED is made for it; every setting can still be changed in "
                   "Display and Performance.", card=card.name) if card else
                 t("Pick a quality level; every setting can still be changed in Display and Performance."))
        custom = self._editor.load().game(self._game).get("preset") not in presets.ORDER
        game = self.gameName
        per_game = t("{game}: custom settings (changed by hand).", game=game) if custom else \
            t("Settings are kept per game: these are {game}'s.", game=game)
        return intro + "\n" + per_game

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
        self._check_arabic(cfg.Config.load())
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
        elif name == i18n.SETTING:
            # Not a game setting: the language model loads, saves and applies it.
            if str(value) in dict(i18n.LANGUAGES):
                self.languageWanted.emit(str(value))
        elif name in controls.SETTING_NAMES:
            self._do(lambda: self._editor.set_control(self._scope, name, value))
        elif PER_GAME_ROW in name:
            setting, _, key = name.partition(PER_GAME_ROW)
            self._do(lambda: self._editor.set(key, setting, value))
        else:
            self._do(lambda: self._editor.set(self._game, name, value))

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        self._do(lambda: self._editor.apply_preset(self._game, name))

    @Slot(str, int)
    def startCapture(self, action: str, slot: int) -> None:
        self._capture = (action, slot)
        self._hint = t("Press a key or a mouse button, or turn the wheel.")
        self._capture_timer.start()
        self.changed.emit()

    @Slot()
    def cancelCapture(self) -> None:
        if self._capture:
            self._capture = None
            self._hint = ""
            self.changed.emit()

    @Slot(int, int, int)
    def captureKey(self, key: int, scancode: int, modifiers: int) -> None:
        if not self._capture:
            return
        name = sdl_key_name(key, scancode, modifiers)
        if name in input_map.RESERVED_KEYS:
            self._end_capture(t("{key} belongs to the game window (Insert: the menu, Left Alt: frees the mouse). "
                                "Choose another key.", key=name))
        elif not name:
            self._end_capture(t("That key can't be used in the game. Choose another key."))
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
            self.notice.emit(t("Not saved: {error}", error=error))
        self.changed.emit()

    def _sync(self, key: str) -> None:
        try:
            self._editor.sync_controls(key)
        except OSError as error:
            self.notice.emit(t("Could not read {game}'s controls: {error}", game=games.by_key(key).name,
                               error=error))

    def _bind(self, binding: str) -> None:
        assert self._capture is not None
        action, slot = self._capture
        self._capture = None
        self._capture_timer.stop()
        try:
            self._editor.bind(self._scope, action, slot, binding)
            where = t("all games") if self._scope == controls.ALL else self.controlsScopeName
            self._hint = t("Saved for {where}.", where=where) + " " + t(CAPTURE_HINT)
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
            self.notice.emit(t("Could not save the settings: {error}", error=error))
        self.changed.emit()

    def _check_arabic(self, config: cfg.Config) -> None:
        """Which games have the Arabic translation, found off the UI thread (the first look reads each game's text
        archive); looked for again when the game folder or the update changes."""
        source = (str(config.data.get("game_dir") or ""), "")
        if source == self._arabic_source:
            return
        self._arabic_source = source
        threading.Thread(target=lambda: _send(self._arabic_found, (source, settings.copy_languages(config))),
                         daemon=True).start()

    def _on_arabic_found(self, packet: tuple[tuple[str, str], dict[str, bool]]) -> None:
        source, held = packet
        if source != self._arabic_source:
            return  # the folders changed again while this look ran; the newer look answers
        self._editor.languages = held
        self._editor.arabic = settings.arabic_available(held)
        try:
            moved, back = self._editor.follow_arabic()
        except OSError as error:
            self.notice.emit(t("Could not save the settings: {error}", error=error))
            moved, back = [], []
        if moved:
            names = ", ".join(f"Uncharted {games.by_key(key).number}" for key in moved)
            self.notice.emit(t("This copy of the game has no Arabic translation: {games} now in English.",
                               games=names))
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

    def _row(self, name: str, config: cfg.Config, values: dict[str, Any], enabled: bool = True,
             game: str | None = None) -> dict[str, Any]:
        setting = settings.BY_KEY[name]
        row: dict[str, Any] = {"key": name, "title": t(setting.title), "hint": t(setting.hint), "enabled": enabled}
        if setting.toggle:
            row.update(kind="toggle", checked=bool(values[name]))
        else:
            # The game languages keep their own names (core translates the Arabic translation's label).
            row.update(kind="choice", value=str(values[name]),
                       options=_options(self._editor.options(game or self._game, name, config),
                                        translate=name != "language"))
        return row

    @staticmethod
    def _language_row() -> dict[str, Any]:
        """The launcher's own language (launcher.json "ui_language"), its languages named in their own words."""
        return {"key": i18n.SETTING, "kind": "choice", "title": t("Launcher language"),
                "hint": t("The launcher's own texts and buttons."),
                "enabled": True, "value": i18n.language(), "options": _options(i18n.LANGUAGES, translate=False)}

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
                rows.append({"kind": "note", "text": t("Render size: {size}", size=render.replace("x", " × "))})
            if name == "upscale" and output:
                rows.append({"kind": "note", "text": t("Draws {render}, upscaled to {output}",
                                                       render=render.replace("x", " × "),
                                                       output=output.replace("x", " × "))})
        return rows

    def _performance_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._setting_rows("performance", config, values)
        screen = QGuiApplication.primaryScreen()
        hz = round(screen.refreshRate()) if screen else 60
        note = t("With VSync your monitor's refresh rate ({hz} Hz) is the smoothest limit.", hz=hz)
        if int(values["fps_limit"]) > 60:
            note = t("Frame rate unlocked up to {fps} FPS (your monitor: {hz} Hz).", fps=values["fps_limit"],
                     hz=hz) + " " + note
        rows.insert(1, {"kind": "note", "text": note})
        if self._game == "u2" and int(values["fps_limit"]) > 60:
            # Players' reports (port issues, Nov 2026): above 60 FPS Nate passes through the second blade in "The
            # Path of Light" and chapter 21 (Convoy) crashes after its cutscene; both are fine at 60.
            rows.insert(2, {"kind": "note", "text": t(U2_HIGH_FPS)})
        return rows

    def _controls_rows(self, config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        """One choice at the top says whose keys the tab shows (ALL GAMES, or one game); a game that has keys of
        its own gets one button to take the ALL GAMES keys again. Then the settings and the bindings."""
        scope = self._scope
        scope_options = [{"value": controls.ALL, "label": t("All games")}] + [
            {"value": game.key, "label": t("Uncharted {number} only", number=game.number)} for game in games.GAMES]
        rows: list[dict[str, Any]] = [{"kind": "choice", "key": SCOPE_KEY, "title": t("These keys are for"),
                                       "hint": "", "enabled": True, "value": scope, "options": scope_options}]
        if scope != controls.ALL and controls.own_items(config, scope):
            rows.append({"kind": "button", "title": t("{game} has keys of its own", game=self.controlsScopeName),
                         "hint": t("The other games use the ALL GAMES keys."), "action": "useAllGamesKeys",
                         "arg": "", "label": t("USE THE ALL GAMES KEYS"), "danger": False})
        scope_values = {**values, **self._editor.control_values(scope, config)}
        for setting in settings.in_tab("controls"):
            row = self._row(setting.key, config, scope_values)
            if row["kind"] == "choice":
                row["options"] = _options(self._editor.control_options(scope, setting.key, config))
            rows.append(row)
        if scope == controls.ALL:
            rows.append({"kind": "button", "title": t("Reset controls"),
                         "hint": t("Every key, button and setting back to the defaults."),
                         "action": "resetControls", "arg": "",
                         "label": t("PRESS AGAIN") if self._reset_armed else t("RESET"), "danger": self._reset_armed})
        rows.append({"kind": "note", "text": self._hint or t(CAPTURE_HINT)})
        current = controls.control_set(config, scope)
        style = str(scope_values["prompts"])
        pad_options = [{"value": "", "label": "—"}] + [
            {"value": button, "label": t(input_map.pad_label(button, style))} for button in input_map.PAD_BUTTONS]
        for title, actions in input_map.GROUPS:
            rows.append({"kind": "section", "title": t(title)})
            for action, label in actions:
                bound = current.bindings[action]
                fixed = action not in input_map.PAD_DEFAULTS
                button = input_map.PAD_FIXED.get(action) if fixed else current.pad.get(action)
                rows.append({"kind": "binding", "action": action, "title": t(label),
                             "keys": [t(input_map.label(bound[slot] if slot < len(bound) else None))
                                      for slot in range(input_map.SLOTS)],
                             "capture": [self._capture == (action, slot) for slot in range(input_map.SLOTS)],
                             "pad": t(input_map.pad_label(button, style, action)), "padValue": button or "",
                             "padFixed": fixed, "padOptions": pad_options})
        return rows

    def _layout_rows(self, layout: tuple[Any, ...], config: cfg.Config, values: dict[str, Any]) -> list[dict[str, Any]]:
        """A tab for all games: sections, buttons, settings; a game's own setting gets one row per game."""
        rows: list[dict[str, Any]] = []
        for item in layout:
            if isinstance(item, str):
                if settings.BY_KEY[item].store == settings.GAME:
                    rows += self._per_game_rows(item, config)
                else:
                    rows.append(self._row(item, config, values))
            elif item[0] == "section":
                rows.append({"kind": "section", "title": t(item[1])})
            else:
                _, title, hint, action, argument, label = item
                rows.append({"kind": "button", "title": t(title), "hint": t(hint), "action": action, "arg": argument,
                             "label": t(label), "danger": action == "resetSettings"})
        return rows

    def _per_game_rows(self, name: str, config: cfg.Config) -> list[dict[str, Any]]:
        """One row per game for a setting each game has (its language, its save profile); the hint once, above."""
        rows: list[dict[str, Any]] = [{"kind": "note", "text": t(settings.BY_KEY[name].hint)}]
        for game in games.GAMES:
            values = self._editor.values(game.key, config)
            row = self._row(name, config, values, game=game.key)
            row.update(key=f"{name}{PER_GAME_ROW}{game.key}", title=f"Uncharted {game.number}", hint="")
            rows.append(row)
        return rows

    def _language_rows(self, config: cfg.Config) -> list[dict[str, Any]]:
        self._check_arabic(config)  # a game folder or update chosen since the last look
        return ([{"kind": "section", "title": t("LAUNCHER")}, self._language_row(),
                 {"kind": "section", "title": t("GAMES")}, {"kind": "note", "text": self._arabic_text()}]
                + self._per_game_rows("language", config))

    def _game_info(self, config: cfg.Config) -> dict[str, Any]:
        """The chosen copy at a glance: its folder and whether it has the Arabic translation."""
        game_dir = config.game_dir()
        if not games.is_game_dir(game_dir):
            return {"kind": "note", "text": t("No game folder chosen yet.")}
        return {"kind": "note", "text": "\n".join((t("Game folder: {folder}", folder=game_dir), self._arabic_text()))}

    def _arabic_text(self) -> str:
        """Whether the chosen copy has the Arabic translation, and for which games."""
        found = self._editor.arabic
        if not found:
            return t("Arabic translation: checking this copy...")
        having = [f"Uncharted {games.by_key(key).number}" for key in games.KEYS if found.get(key)]
        if not having:
            return t("Arabic translation: not in this copy (its games are in English).")
        if len(having) == len(games.KEYS):
            return t("Arabic translation: yes, in all three games.")
        return t("Arabic translation: yes, in {games}.", games=", ".join(having))
