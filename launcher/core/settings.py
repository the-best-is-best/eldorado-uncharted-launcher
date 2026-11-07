# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Every setting of the Settings screen in one table (where it is stored, its choices), and the editor that reads
and writes them. Each change is saved at once: launcher.json through config.Config, the game's own
probe-uN.ini through config.write_ini.

Dropped (read by nothing with the current engine, roadmap section 3): async_shaders, mouse_vertical,
mouse_invert_x, low_vram."""
from __future__ import annotations


from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from . import config as cfg
from . import controls, game_files, games, gpu, input_map, paths, presets, resolution
from .i18n import t

# Where a setting lives.
LAUNCHER = "launcher"    # launcher.json, shared by the three games
GAME = "game"            # launcher.json, the game's own entry
INI = "ini"              # the game's probe-uN.ini
CONTROLS = "controls"    # the game's entry and its ini (input_map.to_ini)
EVERY_INI = "every_ini"  # all three games' ini files (the in-game menu is the same in each)
DERIVED = "derived"      # made of other values (upscaling, anti-aliasing, sharpening)

Options = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Setting:
    key: str
    store: str
    tab: str
    title: str
    hint: str = ""
    options: Options = ()  # none: an on/off setting

    @property
    def toggle(self) -> bool:
        return not self.options

    @property
    def default(self) -> Any:
        if self.store == LAUNCHER:
            return cfg.LAUNCHER_DEFAULTS.get(self.key, False)
        if self.store in (GAME, CONTROLS):
            return cfg.GAME_DEFAULTS[self.key]
        if self.store in (INI, EVERY_INI):
            value = cfg.INI_DEFAULTS.get(self.key) or cfg.INI_OPTIONAL_DEFAULTS[self.key]
            return value == "1" if self.toggle else value
        return self.options[0][0] if self.options else False


def _pairs(*values: str) -> Options:
    return tuple((value, value) for value in values)


UPSCALING_TITLES: dict[str, str] = {"off": "Off", "fsr1": "FSR 1", "fsr3": "FSR 3.1", "fsr4": "FSR 4",
                                    "dlss": "DLSS"}
CHEAT_TEXTS: dict[str, tuple[str, str]] = {
    "skipintro": ("Skip intro", "No logo movies at the start (Sony, Naughty Dog, Bluepoint)."),
    "invincible": ("Invincible", "Nate takes no damage."),
    "ammo": ("Infinite ammo", "The magazine never runs empty: no reloading."),
    "grenades": ("Infinite grenades", "Nate never runs out of grenades."),
    "treasures": ("Give all treasures", "Every treasure counts as found in the save you play, a few seconds into "
                  "play. It is written into that save (and earns the treasure trophies), so it stays after the cheat "
                  "is turned off."),
    "rewards": ("Unlock all rewards", "Everything in Bonuses (skins, weapons, render modes, art, gameplay tweaks) "
                "and every cutscene. Nothing is saved: turned off, the menus show your own progress again."),
}
LANGUAGES: Options = (
    # First: not one of the game's languages but a fan translation laid over one of them (tools/arabic_language.py),
    # offered for the games whose copy has it (arabic_available).
    ("ar", "Arabic (translation)"),
    ("1", "English (US)"), ("18", "English (UK)"), ("2", "Français"), ("4", "Deutsch"), ("5", "Italiano"),
    ("3", "Español (España)"), ("20", "Español (Latinoamérica)"), ("7", "Português (Portugal)"),
    ("17", "Português (Brasil)"), ("6", "Nederlands"), ("14", "Dansk"), ("15", "Norsk"), ("13", "Svenska"),
    ("12", "Suomi"), ("16", "Polski"), ("23", "Čeština"), ("25", "Ελληνικά"), ("8", "Русский"), ("19", "Türkçe"),
    ("0", "日本語"), ("9", "한국어"), ("10", "中文 (繁體)"),
)
ARABIC = "ar"
ENGLISH = "1"  # English (US): where a game goes when its copy has no Arabic translation
ARABIC_CACHE = "arabic-language.json"  # in the player's folder, shared with the start script
# Speech packs in a copy of the game (u*data/build/main/sound1/.../<language>_ps4.psarc) -> language ids.
SPEECH_PACKS: dict[str, tuple[str, ...]] = {
    "english": ("1", "18"), "french": ("2",), "german": ("4",), "italian": ("5",), "spanish": ("3", "20"),
    "portuguese": ("7", "17"), "dutch": ("6",), "danish": ("14",), "norwegian": ("15",), "swedish": ("13",),
    "finnish": ("12",), "polish": ("16",), "czech": ("23",), "greek": ("25",), "russian": ("8",),
    "turkish": ("19",), "japanese": ("0",), "korean": ("9",), "chinese": ("10",)}
SPEECH_GLOBS = ("u*data/build/main/sound1/speech/*_ps4.psarc", "u*data/build/main/sound1/streams/speech/*_ps4.psarc")
OVERLAY_ITEMS: tuple[tuple[str, str], ...] = (
    ("overlay_fps", "FPS"), ("overlay_frametime", "Frame time"), ("overlay_gpu", "GPU"), ("overlay_cpu", "CPU"),
    ("overlay_ram", "RAM"), ("overlay_vram", "VRAM"), ("overlay_upscaler", "Upscaler"))

SETTINGS: tuple[Setting, ...] = (
    # Display
    Setting("aspect", GAME, "display", "Aspect ratio",
            "Ultrawide (21:9, 32:9) with Borderless or Fullscreen: more at the sides, the same view top to bottom "
            "as 16:9. 16:10 (Steam Deck: 1280x800) shows more at the top and bottom.", _pairs(*cfg.ASPECTS)),
    Setting("resolution", GAME, "display", "Resolution",
            "How sharp the picture is; higher needs a faster card (the PS4 drew 1080p). With upscaling the game "
            "draws less and is brought up to it. Drake's Fortune draws at most 1620p and scales up.",
            _pairs(*cfg.RESOLUTIONS)),
    Setting("upscaling", DERIVED, "display", "Upscaling",
            "More FPS: the game draws below the resolution and every frame is brought up to it; HUD and menus stay "
            "sharp. FSR 1 is the lightest and works on any card; FSR 3.1, FSR 4 and DLSS (NVIDIA RTX) also use "
            "earlier frames: more detail, and they smooth edges themselves.",
            tuple(UPSCALING_TITLES.items())),
    Setting("upscale", GAME, "display", "Upscaling quality",
            "How far below the resolution the game draws: Quality 1/1.5, Balanced 1/1.7, Performance 1/2, Ultra "
            "Performance 1/3. Native AA (DLAA with DLSS) draws at the resolution and only smooths edges.",
            tuple(presets.QUALITY_TITLES.items())),
    Setting("aa", DERIVED, "display", "Anti-aliasing",
            "Smooths jagged, shimmering edges with upscaling Off or FSR 1 (FSR 3.1, FSR 4 and DLSS do it "
            "themselves).", (("off", "Off"), ("taa", "TAA"))),
    Setting("display_mode", INI, "display", "Display mode",
            "A window, a borderless window (quick Alt+Tab) or fullscreen.",
            (("windowed", "Windowed"), ("borderless", "Borderless"), ("fullscreen", "Fullscreen"))),
    Setting("vsync", INI, "display", "VSync", "No tearing when the camera turns. Best left on."),
    Setting("frame_gen", INI, "display", "Frame generation",
            "AMD FSR 3 adds a frame between every two the game draws: about twice the frames on any card, with a "
            "little more input delay. Best with VSync off or a screen faster than 60 Hz; works with DLSS.",
            (("off", "Off"), ("fsr3", "FSR 3"))),
    Setting("sharpening", DERIVED, "display", "Sharpening", "A crisper final picture (AMD FidelityFX RCAS).",
            (("off", "Off"), ("25", "25%"), ("50", "50%"), ("75", "75%"), ("100", "100%"))),
    Setting("show_fps", INI, "display", "Performance counter",
            "FPS, temperatures and memory in a corner of the screen (also in the in-game menu's Overlay tab)."),
    *(Setting(key, INI, "display", f"Counter: {label}") for key, label in OVERLAY_ITEMS),
    Setting("overlay_corner", INI, "display", "Counter corner", "Where the counter sits.",
            (("0", "Top left"), ("1", "Top right"), ("2", "Bottom left"), ("3", "Bottom right"))),
    Setting("overlay_layout", INI, "display", "Counter layout", "One line, or one item per line.",
            (("0", "One line"), ("1", "Stacked"))),
    Setting("overlay_scale", INI, "display", "Counter size", "The counter's text size.",
            (("75", "75%"), ("100", "100%"), ("125", "125%"), ("150", "150%"), ("200", "200%"))),
    Setting("overlay_opacity", INI, "display", "Counter background",
            "How dark the counter's box is; None leaves the text on the picture.",
            (("0", "None"), ("25", "25%"), ("50", "50%"), ("75", "75%"), ("100", "100%"))),
    # Performance
    Setting("fps_limit", INI, "performance", "Frame rate limit",
            "60 is how the games were made. Higher is smoother but experimental: if the game runs too fast or Nate "
            "falls through the floor, go back to 60.", tuple((value, value) for value in cfg.FPS_LIMITS)),
    Setting("frames_queued", INI, "performance", "Frames queued",
            "Keep 1. 2 can add a few FPS in heavy scenes, but Uncharted 2's characters then float a little above "
            "the floor.", (("1", "1"), ("2", "2"), ("0", "Unlimited"))),
    Setting("multithreaded", GAME, "performance", "Multithreaded rendering",
            "Prepares and records the picture on several CPU cores: more FPS where the CPU is the limit. Turn it "
            "off only to compare."),
    Setting("job_sleep", LAUNCHER, "performance", "Idle game threads",
            "Sleep: the game's helper threads rest while they wait (fast on 4-6 core CPUs, saves power). Spin keeps "
            "their cores busy as on the PS4 (smoother with many cores). Auto: Spin in Uncharted 1 with 8 or more "
            "threads, else Sleep.", (("auto", "Auto"), ("on", "Sleep"), ("off", "Spin"))),
    # Controls: one shared set for the three games, a game's own items on top (core/controls.py).
    Setting("mouse", CONTROLS, "controls", "Mouse", "The mouse moves the camera and aims."),
    Setting("mouse_sens", CONTROLS, "controls", "Mouse sensitivity", "", input_map.SENSITIVITIES),
    Setting("mouse_aim_sens", CONTROLS, "controls", "Aim sensitivity",
            "While aiming, times the mouse sensitivity.", input_map.AIM_FACTORS),
    Setting("mouse_invert", CONTROLS, "controls", "Invert mouse up/down"),
    Setting("vibration", CONTROLS, "controls", "Controller vibration", "Off stops every rumble."),
    Setting("prompts", CONTROLS, "controls", "Button prompts",
            "The button icons in the games' text and menus. Auto follows the device you play with.",
            input_map.PROMPT_STYLES),
    # Cheats
    *(Setting("cheat_" + name, LAUNCHER, "cheats", title, hint)
      for name, (title, hint) in CHEAT_TEXTS.items()),
    Setting("unlock", LAUNCHER, "cheats", "Unlock all chapters",
            "Every chapter in Chapter Select and Brutal difficulty from the start, in all three games. Your saves "
            "and progress stay as they are."),
    # Game files
    Setting("save_profile", GAME, "files", "Save profile",
            "Separate saves for this game, like another PS4 user: each profile keeps its own progress and in-game "
            "settings. Profile 1 has your earlier saves; switching never deletes anything.",
            (("1", "Profile 1"), ("2", "Profile 2"), ("3", "Profile 3"))),
    Setting("language", GAME, "language", "Language",
            "The game's menus and subtitles: pick it here, then press Square in the "
            "game's main menu. Languages marked + voices are spoken in your copy too. Arabic (translation) appears "
            "only when this game's copy has the Arabic translation update.", LANGUAGES),
    Setting("anisotropy", LAUNCHER, "display", "Texture filtering",
            "Sharper ground and walls seen at an angle, in all three games; 16x costs almost nothing. Game = as on "
            "the PS4.", (("0", "Game"), ("4", "4x"), ("8", "8x"), ("16", "16x"))),
    Setting("no_dof", LAUNCHER, "display", "No depth of field (Uncharted 2 and 3)",
            "Turns off the background blur (aiming, cutscenes, play). Needs update 1.02."),
    Setting("menu_shortcut", EVERY_INI, "controls", "In-game menu shortcut",
            "The controller buttons that open the in-game menu (all games). L2 + R3 also zooms the scope with some "
            "guns: pick Select + Start or Keyboard only (Insert) then.",
            (("lt_r3", "L2 + R3"), ("view_menu", "Select + Start"), ("keyboard", "Keyboard only"))),
    Setting("check_updates", LAUNCHER, "launcher", "Check for updates at start",
            "The launcher asks before it installs anything."),
    Setting("diagnostics", LAUNCHER, "launcher", "Performance log",
            "Frame rate statistics in the log every 5 seconds: helps when you report a problem."),
)
BY_KEY: dict[str, Setting] = {setting.key: setting for setting in SETTINGS}
TABS: tuple[tuple[str, str], ...] = (("setup", "QUICK SETUP"), ("display", "DISPLAY"),
                                     ("performance", "PERFORMANCE"), ("controls", "CONTROLS"), ("language", "LANGUAGE"),
                                     ("files", "GAME FILES"), ("launcher", "LAUNCHER"), ("cheats", "CHEATS"))
# The tabs that show one game's settings (the others: all games, or each game on its own row).
PER_GAME_TABS: tuple[str, ...] = ("setup", "display", "performance")


def in_tab(tab: str) -> list[Setting]:
    return [setting for setting in SETTINGS if setting.tab == tab]


def upscaling_options(root: Path | None = None) -> Options:
    """Off, FSR 1 and FSR 3.1 always; FSR 4 when its model files are installed; DLSS when its DLLs are beside the
    engine (engine/bin in a package, engine/out in a build)."""
    root = root or paths.ROOT
    names = ["off", "fsr1", "fsr3"]
    if (root / "engine" / "fsr4_shaders" / "fsr4_model_v07_i8_native_1080_pre.spv").is_file():
        names.append("fsr4")
    if any((folder / "bbport_dlss.dll").is_file() and (folder / "nvngx_dlss.dll").is_file()
           for folder in (root / "engine" / "bin", root / "engine" / "out")):
        names.append("dlss")
    return tuple((name, UPSCALING_TITLES[name]) for name in names)


def voice_languages(game_dir: Path | None) -> set[str]:
    """The language ids with speech in this copy of the game."""
    ids: set[str] = set()
    if game_dir and game_dir.is_dir():
        for pattern in SPEECH_GLOBS:
            for pack in game_dir.glob(pattern):
                ids.update(SPEECH_PACKS.get(pack.name.removesuffix("_ps4.psarc").lower(), ()))
    return ids


def arabic_finder() -> ModuleType:
    """tools/arabic_language.py, the start script's finder of the translation (loaded by path, not copied)."""
    return game_files.tool_module("arabic_language")


def arabic_available(config: cfg.Config, log: Callable[[str], None] = print) -> dict[str, bool]:
    """Which games have the Arabic translation in the player's copy: the start script's finder on each game's
    core.psarc as the engine gets it, the update's when the update has one (the game update is laid over the game
    at a start), else the game's. The finder keeps its answer by the archive's size and time, so only the first call
    reads an archive (seconds). A game whose texts cannot be read is False, with the reason on a log line."""
    found = dict.fromkeys(games.KEYS, False)
    game_dir = config.game_dir()
    if not games.is_game_dir(game_dir):
        return found
    try:
        finder = arabic_finder()
    except game_files.GameFilesError as error:
        log(f"Arabic: not looked for: {error}")
        return found
    update = game_files.update_in_use(config)
    cache = paths.USER_DIR / ARABIC_CACHE
    for key in games.KEYS:
        archive = Path(finder.DATA_DIRS[key]) / "build" / "main" / "core.psarc"
        root = update if update and (update / archive).is_file() else game_dir
        try:
            found[key] = finder.find_arabic_language(root, key, cache) is not None
        except Exception as error:  # a damaged archive: the choice is not offered, nothing else changes
            log(f"Arabic: {games.by_key(key).name}: the texts could not be read ({error})")
    return found


def resolution_label(value: str, aspect: str) -> str:
    """A resolution by the height the game draws at this aspect ratio (720p is 800p at 16:10); 2160 is 4K."""
    height = int(resolution.at_aspect(value, aspect).split("x")[1])
    return "4K" if height == 2160 else f"{height}p"


def anti_aliasing(ini: dict[str, str], game: dict[str, Any]) -> str:
    """TAA or off: the ini's upscaler with Off and FSR 1; kept in the game's entry while a temporal upscaler
    (which smooths edges itself) holds the ini's value."""
    upscaler = ini.get("upscaler", cfg.INI_DEFAULTS["upscaler"])
    if upscaler in ("off", "taa"):
        return upscaler
    return "taa" if game.get("aa") == "taa" else "off"


def sharpening(ini: dict[str, str]) -> str:
    return ini.get("rcas_strength", "75") if ini.get("rcas", "1") == "1" else "off"


class Editor:
    """Reads and changes the settings. Every call reads launcher.json and the ini again (the released launcher,
    the home screen or the in-game menu may have changed them) and saves what it changes at once."""

    def __init__(self, file: Path | None = None, card: gpu.Gpu | None = None,
                 arabic: dict[str, bool] | None = None) -> None:
        self.file = file
        self.card = card
        self.upscalers = upscaling_options()
        # The games whose copy has the Arabic translation (arabic_available; a game missing from it has none).
        # None: not looked for, so every game may choose it, as the released launcher offers it.
        self.arabic = arabic

    # --- reading ------------------------------------------------------------------------------------------------

    def load(self) -> cfg.Config:
        return cfg.Config.load(self.file)

    def values(self, key: str, config: cfg.Config | None = None) -> dict[str, Any]:
        """Every setting's value for a game (toggles as bool, choices as str)."""
        config = config or self.load()
        game, ini = config.game(key), cfg.read_ini(key)
        result: dict[str, Any] = {}
        for setting in SETTINGS:
            if setting.store == LAUNCHER:
                value = config.data.get(setting.key, setting.default)
            elif setting.store in (GAME, CONTROLS):
                value = game.get(setting.key, setting.default)
            elif setting.store in (INI, EVERY_INI):
                raw = ini.get(setting.key, cfg.INI_OPTIONAL_DEFAULTS.get(setting.key, ""))
                value = raw == "1" if setting.toggle else raw
            else:
                value = {"upscaling": resolution.upscaler(ini), "aa": anti_aliasing(ini, game),
                         "sharpening": sharpening(ini)}[setting.key]
            result[setting.key] = bool(value) if setting.toggle else str(value)
        return result

    def options(self, key: str, name: str, config: cfg.Config | None = None) -> Options:
        """A setting's choices for a game (some depend on other values and on this PC)."""
        setting = BY_KEY[name]
        config = config or self.load()
        game = config.game(key)
        if name == "upscaling":
            return self.upscalers
        if name == "resolution":
            return tuple((value, resolution_label(value, game.get("aspect", "16:9"))) for value in cfg.RESOLUTIONS)
        if name == "upscale":
            upscaler = resolution.upscaler(cfg.read_ini(key))
            choices = [(value, "DLAA" if value == "off" and upscaler == "dlss" else title)
                       for value, title in setting.options if not (upscaler == "fsr1" and value == "off")]
            return tuple(choices)
        if name == "language":
            voices = voice_languages(config.game_dir())
            # The languages' own names stay as written; the translation's label and the voices mark are the
            # launcher's texts.
            return tuple((value, (t("Arabic (translation)") if value == ARABIC else title) +
                          ("  " + t("(+ voices)") if value in voices else ""))
                         for value, title in LANGUAGES if value != ARABIC or self.offers_arabic(key, game))
        if name in ("mouse_sens", "mouse_aim_sens"):
            current = str(game.get(name, "1.0"))
            if current not in dict(setting.options):  # a value the in-game menu set
                return setting.options + ((current, f"{current}x"),)
        return setting.options

    def offers_arabic(self, key: str, game: dict[str, Any]) -> bool:
        """The Arabic translation is a choice for a game whose copy has it (and while the copy is not looked at
        yet, for a game that has it chosen)."""
        if self.arabic is None or self.arabic.get(key, False):
            return True
        return key not in self.arabic and str(game.get("language", "")) == ARABIC

    def drop_missing_arabic(self) -> list[str]:
        """A game set to the Arabic translation whose copy has none (another game folder chosen) goes back to
        English. Returns those games."""
        if not self.arabic:
            return []
        config = self.load()
        changed = [key for key in games.KEYS
                   if str(config.game(key).get("language")) == ARABIC and not self.arabic.get(key, False)]
        for key in changed:
            config.game(key)["language"] = ENGLISH
        if changed:
            config.save()
        return changed

    def preset_list(self) -> list[presets.Preset]:
        return presets.all_for(self.card, {name for name, _ in self.upscalers})

    def sizes(self, key: str, config: cfg.Config | None = None) -> tuple[str, str | None]:
        config = config or self.load()
        return resolution.sizes(config.game(key), cfg.read_ini(key))

    # --- changing -----------------------------------------------------------------------------------------------

    def set(self, key: str, name: str, value: Any) -> None:
        """Changes one setting of a game (a shared one for all games) and saves it."""
        games.by_key(key)
        setting = BY_KEY[name]
        config = self.load()
        if setting.toggle:
            value = bool(value)
        else:
            value = str(value)
            if value not in dict(self.options(key, name, config)):
                raise ValueError(f"{setting.title}: no choice {value!r}")
        game = config.game(key)
        if setting.store == LAUNCHER:
            config.data[name] = value
            config.save()
        elif setting.store == GAME:
            game[name] = value
            if name == "resolution":
                game["preset"] = "custom"
            config.save()
        elif setting.store == CONTROLS:
            self.set_control(key, name, value)
        elif setting.store == INI:
            self._change_ini(config, key, {name: ("1" if value else "0") if setting.toggle else value})
        elif setting.store == EVERY_INI:
            for other in games.KEYS:
                cfg.write_ini(other, {name: value})
        elif name == "upscaling":
            self._set_upscaling(config, key, value)
        elif name == "aa":
            game["aa"] = value
            config.save()
            self._change_ini(config, key, {"upscaler": value})
        elif name == "sharpening":
            self._change_ini(config, key, {"rcas": "0"} if value == "off" else {"rcas_strength": value, "rcas": "1"})

    def apply_preset(self, key: str, name: str) -> None:
        preset = presets.resolve(name, self.card, {option for option, _ in self.upscalers})
        config = self.load()
        game, ini = config.game(key), cfg.read_ini(key)
        game["resolution"], game["upscale"] = preset.resolution, preset.upscale
        ini.update(preset.values)
        if preset.kind == "igpu":
            # On an integrated GPU the command thread is the limit; multithreaded rendering takes part of it.
            game["multithreaded"] = True
            game["aa"] = "off"
        if name == "recommended":
            if preset.upscaler:
                game["aa"] = "off"
            if preset.values.get("upscaler") == "taa":
                game["aa"] = "taa"
        game["preset"] = name
        config.save()
        cfg.write_ini(key, {setting: ini[setting] for setting in cfg.INI_DEFAULTS})

    # --- controls: ALL GAMES (controls.ALL) or one game's own items (core/controls.py) ------------------------------

    def sync_controls(self, key: str) -> None:
        """The game's ini as the in-game menu left it: into the shared set, or the game's own items for the items
        it owns."""
        controls.sync_from_ini(self.load(), key)

    def control_set(self, scope: str) -> controls.ControlSet:
        """What ALL GAMES or one game uses: every binding, controller button and setting."""
        return controls.control_set(self.load(), scope)

    def control_values(self, scope: str, config: cfg.Config | None = None) -> dict[str, Any]:
        """The mouse and controller settings of a scope (toggles as bool, choices as str)."""
        settings_of = controls.control_set(config or self.load(), scope).settings
        return {name: bool(value) if BY_KEY[name].toggle else str(value) for name, value in settings_of.items()}

    def control_options(self, scope: str, name: str, config: cfg.Config | None = None) -> Options:
        setting = BY_KEY[name]
        if name in ("mouse_sens", "mouse_aim_sens"):
            current = str(controls.control_set(config or self.load(), scope).settings[name])
            if current not in dict(setting.options):  # a value the in-game menu set
                return setting.options + ((current, f"{current}x"),)
        return setting.options

    def set_control(self, scope: str, name: str, value: Any) -> None:
        """One of the mouse/controller settings for ALL GAMES, or for one game (its own value from then on)."""
        setting = BY_KEY[name]
        if setting.store != CONTROLS:
            raise KeyError(f"{name} is not a control setting")
        config = self.load()
        if setting.toggle:
            value = bool(value)
        else:
            value = str(value)
            if value not in dict(self.control_options(scope, name, config)):
                raise ValueError(f"{setting.title}: no choice {value!r}")
        controls.set_item(config, scope, controls.Item("setting", name), value)

    def bind(self, scope: str, action: str, slot: int, binding: str | None) -> None:
        controls.set_binding(self.load(), scope, action, slot, binding)

    def bind_pad(self, scope: str, action: str, button: str | None) -> None:
        controls.set_pad(self.load(), scope, action, button)

    def reset_controls(self, scope: str) -> None:
        """ALL GAMES: the defaults (a game's own items stay its own). A game: its own items dropped."""
        controls.reset(self.load(), scope)

    def clear_own(self, key: str, item: controls.Item | None = None) -> None:
        controls.clear_own(self.load(), key, item)

    def make_shared(self, key: str) -> None:
        controls.make_shared(self.load(), key)

    def own_summary(self, config: cfg.Config | None = None) -> list[dict[str, Any]]:
        """Each game, how many items it owns and which (by their labels), for the Controls tab."""
        config = config or self.load()
        return [{"key": game.key, "name": f"Uncharted {game.number}",
                 "ownCount": len(controls.own_items(config, game.key)),
                 "ownText": controls.differences_text(config, game.key)} for game in games.GAMES]

    def remember_card(self, card: gpu.Gpu | None) -> None:
        """The detected card, kept in launcher.json ("gpu") as the released launcher does."""
        self.card = card
        if card:
            config = self.load()
            if config.data.get("gpu") != card.name:
                config.data["gpu"] = card.name
                config.save()

    # --- helpers --------------------------------------------------------------------------------------------------

    def _change_ini(self, config: cfg.Config, key: str, updates: dict[str, str]) -> None:
        """An ini setting changed by hand: the game's settings are custom from now on."""
        cfg.write_ini(key, updates)
        game = config.game(key)
        if game.get("preset") != "custom":
            game["preset"] = "custom"
            config.save()

    def _set_upscaling(self, config: cfg.Config, key: str, value: str) -> None:
        """A temporal upscaler takes the ini's upscaler value (TAA is kept in the entry for Off and FSR 1); FSR 1
        has no Native AA (it would do nothing)."""
        game, ini = config.game(key), cfg.read_ini(key)
        aa = anti_aliasing(ini, game)
        game["aa"] = aa
        if value == "fsr1" and game.get("upscale", "off") == "off":
            game["upscale"] = "quality"
        config.save()
        cfg.write_ini(key, {"fsr1": "1" if value == "fsr1" else "0"})
        self._change_ini(config, key, {"upscaler": value if value in resolution.TEMPORAL_UPSCALERS else aa})

