# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Settings screen's core: GPU classes, presets, bindings, and what v2 writes (the start script's environment,
probe-uN.ini, the game entries of launcher.json) compared with the released launcher for the same settings, every
preset and game.

The released launcher (legacy/launcher-tk) imports Tk and Pillow: it is loaded in a second process by the packaged
Python of the installed launcher (..\\Launcher 2\\python), which has both, and driven through its own methods with
the window parts stubbed. Without that Python the comparison is skipped.

usage: python tests/test_core_settings.py        runs every test (pytest finds them too)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "launcher"))

from core import config as cfg  # noqa: E402
from core import games, gpu, input_map, launch, paths, presets, settings  # noqa: E402

LEGACY_DIR = REPO / "legacy" / "launcher-tk"
LEGACY_PYTHON = REPO.parent / "Launcher 2" / "python" / "python.exe"
# Read by nothing any more (dropped in v2): not compared.
DROPPED_INI = {"async_shaders", "mouse_vertical", "mouse_invert_x"}
ENV_NAMES = {"UNCHARTED_DIAGNOSTICS", "UNCHARTED_JOB_SLEEP", "UNCHARTED_LANGUAGE", "UNCHARTED_ANISOTROPY",
             "UNCHARTED_NO_DOF", "UNCHARTED_UNLOCK", "UNCHARTED_CHEATS", "UNCHARTED_UPDATE"}
ENV_PREFIXES = ("UNCHARTED_RESOLUTION_", "UNCHARTED_OUTPUT_RES_", "UNCHARTED_MULTITHREADED_",
                "UNCHARTED_SAVE_PROFILE_", "UNCHARTED_LANGUAGE_")
GAME_KEYS_COMPARED = {"preset": "medium", "resolution": "1920x1080", "aspect": "16:9", "upscale": "off", "aa": "off",
                      "multithreaded": True, "save_profile": "1", "language": "1", "controls": None,
                      "pad_controls": None, "mouse": True, "mouse_sens": "1.0", "mouse_invert": False,
                      "prompts": "auto", "mouse_aim_sens": "1.0", "vibration": True}
CARDS: tuple[tuple[str | None, bool | None], ...] = (
    (None, None), ("NVIDIA GeForce RTX 3060 Laptop GPU", False), ("AMD Radeon RX 9070 XT", False),
    ("AMD Radeon 780M Graphics", True), ("Intel(R) UHD Graphics 620", None), ("NVIDIA GeForce GTX 1050", None),
    ("AMD Radeon(TM) Vega 8 Graphics", True), ("Intel(R) Iris(R) Xe Graphics", None))
CHANGES: tuple[list[list[Any]], ...] = (
    [["preset", "medium"], ["set", "upscaling", "dlss"], ["set", "upscale", "quality"]],
    [["set", "upscaling", "fsr1"]],
    [["set", "aa", "taa"], ["set", "upscaling", "fsr3"], ["set", "upscaling", "off"]],
    [["set", "sharpening", "off"]],
    [["set", "sharpening", "25"]],
    [["set", "resolution", "2560x1440"], ["set", "aspect", "21:9"]],
    [["set", "aspect", "16:10"], ["set", "upscaling", "dlss"], ["set", "upscale", "performance"]],
    [["set", "display_mode", "fullscreen"], ["set", "vsync", False], ["set", "fps_limit", "120"],
     ["set", "frames_queued", "2"], ["set", "frame_gen", "fsr3"], ["set", "show_fps", False],
     ["set", "overlay_gpu", True], ["set", "overlay_corner", "3"], ["set", "overlay_scale", "150"]],
    [["set", "multithreaded", False], ["set", "save_profile", "2"], ["set", "language", "ar"],
     ["set", "job_sleep", "off"], ["set", "anisotropy", "16"], ["set", "no_dof", True], ["set", "unlock", True],
     ["set", "cheat_ammo", True], ["set", "cheat_skipintro", True], ["set", "cheat_rewards", True],
     ["set", "diagnostics", False]],
    [["set", "menu_shortcut", "keyboard"]],
    [["bind", "r2", 0, "key:G"], ["bind", "cross", 1, "mouse:x1"], ["bind", "l1", 0, None],
     ["bind", "ls_up", 1, "key:Up"], ["pad", "cross", "b"], ["pad", "options", None]],
    [["set", "mouse_sens", "2.0"], ["set", "mouse_aim_sens", "5.0"], ["set", "mouse_invert", True],
     ["set", "vibration", False], ["set", "prompts", "xbox"], ["set", "mouse", False]],
    [["bind", "r2", 0, "key:G"], ["pad", "cross", "b"], ["set", "mouse_sens", "3.0"], ["reset_controls"]],
    [["preset", "ultra"], ["set", "upscaling", "dlss"], ["preset", "high"]],
    [["preset", "low"], ["set", "upscaling", "off"], ["set", "aa", "taa"], ["preset", "recommended"]],
)


def scenarios() -> list[dict[str, Any]]:
    result = []
    for key in games.KEYS:
        for name in presets.PRESETS:
            result.append({"game": key, "card": None, "integrated": None, "ops": [["preset", name]]})
        for card, integrated in CARDS:
            result.append({"game": key, "card": card, "integrated": integrated, "ops": [["preset", "recommended"]]})
            if card:
                result.append({"game": key, "card": card, "integrated": integrated, "ops": [["preset", "igpu"]]})
    for key in ("u1", "u3"):
        for ops in CHANGES:
            result.append({"game": key, "card": "NVIDIA GeForce RTX 3060 Laptop GPU", "integrated": False, "ops": ops})
    return result


# --- the shared start of every run ------------------------------------------------------------------------------

def _prepare(folder: Path, key: str) -> Path:
    """A fake game folder and a launcher.json of the current version choosing `key`."""
    game_dir = folder / "game"
    (game_dir / "sce_sys").mkdir(parents=True)
    (game_dir / "eboot.bin").write_bytes(b"")
    (game_dir / "sce_sys" / "param.sfo").write_bytes(b"")
    file = folder / "launcher.json"
    file.write_text(json.dumps({"version": cfg.CONFIG_VERSION, "game": key, "game_dir": str(game_dir)}),
                    encoding="utf-8")
    return file


def _result(env: dict[str, str], ini: dict[str, dict[str, str]], file: Path) -> dict[str, Any]:
    stored = json.loads(file.read_text(encoding="utf-8")).get("games") or {}
    return {"env": {name: value for name, value in env.items()
                    if name in ENV_NAMES or name.startswith(ENV_PREFIXES)},
            "ini": {key: {name: value for name, value in values.items() if name not in DROPPED_INI}
                    for key, values in ini.items()},
            "games": {key: _game_values(stored.get(key) or {}) for key in games.KEYS}}


def _game_values(entry: dict[str, Any]) -> dict[str, Any]:
    """A game's entry as it acts: the bindings in full (a missing table is the defaults)."""
    values = {name: entry.get(name, default) for name, default in GAME_KEYS_COMPARED.items()}
    values["controls"] = input_map.bindings(values["controls"])
    values["pad_controls"] = input_map.pad_buttons(values["pad_controls"])
    return values


# --- v2 ---------------------------------------------------------------------------------------------------------

def run_v2(scenario: dict[str, Any]) -> dict[str, Any]:
    key = scenario["game"]
    saved_user_dir = paths.USER_DIR
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        paths.USER_DIR = folder / "user"
        try:
            file = _prepare(folder, key)
            card = gpu.Gpu(scenario["card"], scenario["integrated"]) if scenario["card"] else None
            editor = settings.Editor(file, card)
            for each in games.KEYS:
                editor.sync_controls(each)
            for op in scenario["ops"]:
                _v2_op(editor, key, op)
            config = cfg.Config.load(file)
            for each in games.KEYS:  # as launch.Session does before a start
                current = cfg.read_ini(each)
                cfg.write_ini(each, {name: current[name] for name in cfg.INI_DEFAULTS})
            return _result(launch.environment(config, {}), {each: cfg.read_ini(each) for each in games.KEYS}, file)
        finally:
            paths.USER_DIR = saved_user_dir


def _v2_op(editor: settings.Editor, key: str, op: list[Any]) -> None:
    kind = op[0]
    if kind == "preset":
        editor.apply_preset(key, op[1])
    elif kind == "set":
        editor.set(key, op[1], op[2])
    elif kind == "bind":
        editor.bind(key, op[1], op[2], op[3])
    elif kind == "pad":
        editor.bind_pad(key, op[1], op[2])
    elif kind == "reset_controls":
        editor.reset_controls(key)
    else:
        raise ValueError(op)


# --- the released launcher (run by the installed launcher's Python) -------------------------------------------------

def run_legacy(scenarios_file: Path, out_file: Path) -> None:
    from importlib.machinery import SourceFileLoader
    from importlib.util import module_from_spec, spec_from_loader

    sys.path.insert(0, str(LEGACY_DIR))
    os.environ["APPDATA"] = tempfile.mkdtemp()
    loader = SourceFileLoader("legacy_launcher", str(LEGACY_DIR / "uncharted_launcher.pyw"))
    spec = spec_from_loader(loader.name, loader)
    assert spec is not None
    legacy = module_from_spec(spec)
    loader.exec_module(legacy)
    # The same engine files (DLSS, FSR 4) decide the upscalers on both sides; the released launcher looks for them
    # in gow3_pc\ (the engine's folder before 2.0): a folder whose gow3_pc is a junction to engine\.
    import _winapi

    view = Path(tempfile.mkdtemp())
    _winapi.CreateJunction(str(REPO / "engine"), str(view / "gow3_pc"))
    import atexit

    atexit.register(os.rmdir, view / "gow3_pc")  # the junction alone (rmdir never enters it)
    legacy.ROOT = view

    class Anything:
        def __getattr__(self, name: str) -> Any:
            return lambda *args, **kwargs: None

    captured: dict[str, str] = {}

    def popen(*args: Any, env: dict[str, str] | None = None, **kwargs: Any) -> Any:
        captured.clear()
        captured.update(env or {})
        raise OSError("not started in the comparison")

    legacy.subprocess.Popen = popen
    legacy.messagebox = Anything()
    legacy.messagebox.askyesno = lambda *args, **kwargs: True

    class Driven(legacy.Launcher):
        def __init__(self, card: str | None, integrated: bool | None) -> None:  # the window-free part of it
            self.config = legacy.read_config()
            for each in legacy.GAME_KEYS:
                if not legacy.controls_from_ini(legacy.read_ini(each), self.config["games"][each]):
                    legacy.write_ini(each, legacy.controls_to_ini(self.config["games"][each]))
            self.reload_ini()
            self.widgets, self.gpu_name = {}, card
            self.controls_hint, self.root = Anything(), Anything()
            self.capturing = self.pad_capture = None
            legacy.PRESETS["recommended"] = legacy.recommended_preset(card, integrated)
            legacy.write_config(self.config)

        def __getattr__(self, name: str) -> Any:  # the drawing methods
            return lambda *args, **kwargs: True

    for name in ("redraw_presets", "refresh_render_size", "update_fps_note", "sync_sharpening", "refresh_controls",
                 "refresh_bindings", "refresh_pad_slots", "set_status", "stop_capture", "confirm_without_update",
                 "confirm_update_files", "confirm_slow_drive"):
        setattr(Driven, name, lambda self, *args, **kwargs: True)

    results = []
    for scenario in json.loads(scenarios_file.read_text(encoding="utf-8")):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            legacy.USER_DIR = folder / "user"
            legacy.INI_FILE = legacy.USER_DIR / "probe.ini"
            legacy.CONFIG_FILE = legacy.PREFIX_CONFIG_FILE = file = _prepare(folder, scenario["game"])
            legacy.RUN_SCRIPT = folder / "probe_uncharted.py"
            legacy.RUN_SCRIPT.write_text("", encoding="utf-8")
            launcher = Driven(scenario["card"], scenario["integrated"])
            for op in scenario["ops"]:
                _legacy_op(legacy, launcher, op)
            launcher.play()
            results.append(_result(dict(captured), {each: legacy.read_ini(each) for each in legacy.GAME_KEYS}, file))
    out_file.write_text(json.dumps(results), encoding="utf-8")


def _legacy_op(legacy: Any, launcher: Any, op: list[Any]) -> None:
    kind = op[0]
    if kind == "preset":
        launcher.apply_preset(op[1])
    elif kind == "bind":
        launcher.set_binding(op[1], op[2], op[3])
    elif kind == "pad":
        launcher.set_pad_binding(op[1], op[2])
    elif kind == "reset_controls":
        launcher.reset_controls()
    elif kind == "set":
        name, value = op[1], op[2]
        store = settings.BY_KEY[name].store
        special = {"upscaling": launcher.change_upscaling, "aa": launcher.change_anti_aliasing,
                   "sharpening": launcher.change_sharpening, "resolution": launcher.change_resolution,
                   "aspect": launcher.change_aspect}
        if name in special:
            special[name](value)
        elif name == "menu_shortcut":  # the released launcher's Advanced row: every game's ini
            launcher.ini["menu_shortcut"] = value
            for each in legacy.GAME_KEYS:
                legacy.write_ini(each, {"menu_shortcut": value})
        elif store == settings.INI:
            launcher.change(name, ("1" if value else "0") if isinstance(value, bool) else value)
        elif store in (settings.GAME, settings.CONTROLS):
            launcher.change_game_setting(name, value)
        else:
            launcher.change_config(name, value)
    else:
        raise ValueError(op)


_legacy_results: list[dict[str, Any]] | None = None


def legacy_results(cases: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    global _legacy_results
    if not LEGACY_PYTHON.is_file():
        print(f"skipped: no {LEGACY_PYTHON} to run the released launcher")
        return None
    if _legacy_results is None:
        with tempfile.TemporaryDirectory() as temporary:
            given, out = Path(temporary) / "scenarios.json", Path(temporary) / "legacy.json"
            given.write_text(json.dumps(cases), encoding="utf-8")
            run = subprocess.run([str(LEGACY_PYTHON), "-X", "utf8", str(Path(__file__).resolve()), "--legacy",
                                  str(given), str(out)], capture_output=True, text=True, encoding="utf-8")
            if run.returncode != 0:
                raise AssertionError(f"the released launcher's run failed:\n{run.stdout}\n{run.stderr}")
            _legacy_results = json.loads(out.read_text(encoding="utf-8"))
    return _legacy_results


def _differences(expected: Any, got: Any, where: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(got, dict):
        found = []
        for name in sorted(set(expected) | set(got)):
            found += _differences(expected.get(name, "<missing>"), got.get(name, "<missing>"), f"{where}.{name}")
        return found
    return [] if expected == got else [f"{where}: legacy {expected!r}, v2 {got!r}"]


# --- tests --------------------------------------------------------------------------------------------------------

def test_v2_writes_what_the_released_launcher_writes() -> None:
    cases = scenarios()
    expected = legacy_results(cases)
    if expected is None:
        return
    problems = []
    for case, legacy in zip(cases, expected):
        for line in _differences(legacy, run_v2(case)):
            problems.append(f"{case['game']} {case['card']} {case['ops']}: {line}")
    assert not problems, f"{len(problems)} differences:\n" + "\n".join(problems[:40])


def test_gpu_classes() -> None:
    assert gpu.tier("NVIDIA GeForce RTX 3060 Laptop GPU") == "medium"
    assert gpu.tier("NVIDIA GeForce RTX 4090") == "ultra"
    assert gpu.tier("AMD Radeon RX 7900 XTX") == "ultra"
    assert gpu.tier("AMD Radeon RX 580") == "medium"
    assert gpu.recommendation("AMD Radeon 780M Graphics") == "igpu"
    assert gpu.recommendation("AMD Radeon 8060S Graphics") == "medium"
    assert gpu.recommendation("Intel(R) Arc(TM) A770 Graphics") == "medium"
    assert gpu.igpu_class("AMD Radeon(TM) Vega 8 Graphics") == "weak"
    assert gpu.strongest(["Intel(R) UHD Graphics 630", "NVIDIA GeForce GTX 1660 SUPER"]) == \
        gpu.Gpu("NVIDIA GeForce GTX 1660 SUPER")


def test_gpu_from_the_engines_log() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        log = Path(temporary) / "boot.log"
        log.write_text("x\nGPU: AMD Radeon 780M Graphics (integrated), 2048 MiB VRAM, driver 2.0\n", encoding="utf-8")
        assert gpu.from_logs([log]) == gpu.Gpu("AMD Radeon 780M Graphics", True, 2048)
        log.write_text("GPU 0: NVIDIA GeForce RTX 3060 (DiscreteGpu)\nGPU: using NVIDIA GeForce RTX 3060\n",
                       encoding="utf-8")
        assert gpu.from_logs([log]) == gpu.Gpu("NVIDIA GeForce RTX 3060", False)


def test_recommended_takes_the_cards_upscaler() -> None:
    rtx = presets.recommended(gpu.Gpu("NVIDIA GeForce RTX 3060 Laptop GPU"), {"dlss", "fsr4"})
    assert (rtx.base, rtx.upscaler, rtx.upscale, rtx.values["upscaler"]) == ("medium", "dlss", "quality", "dlss")
    unknown = presets.recommended(None, {"dlss"})
    assert (unknown.base, unknown.values["upscaler"]) == ("medium", "taa")
    weak = presets.recommended(gpu.Gpu("AMD Radeon(TM) Vega 8 Graphics", True), set())
    assert (weak.upscale, weak.values["fps_limit"]) == ("ultra", "30")


def test_bindings_round_trip_through_the_ini() -> None:
    controls = input_map.bind(None, "r2", 0, "key:G")
    controls = input_map.bind(controls, "cross", 1, "key:G")  # G leaves Fire
    assert controls["r2"] == [] and controls["cross"] == ["key:Space", "key:G"]
    pad = input_map.bind_pad(None, "cross", "b")
    assert pad == {"cross": "b", "circle": "a"}
    ini = input_map.to_ini({"controls": controls, "pad_controls": pad, "mouse_sens": "2.0"})
    back = input_map.from_ini(ini)
    assert back is not None
    assert back["controls"] == input_map.bindings(controls) and back["pad_controls"] == pad
    assert back["mouse_sens"] == "2.0"
    assert input_map.from_ini({"mouse_sens": "1.0"}) is None


def test_every_setting_has_a_default_and_a_tab() -> None:
    tabs = {key for key, _ in settings.TABS}
    for setting in settings.SETTINGS:
        assert setting.tab in tabs, setting.key
        setting.default  # noqa: B018 (raises for a setting without one)


def _run_all() -> int:
    failed = 0
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            try:
                test()
                print(f"ok    {name}")
            except AssertionError as error:
                failed += 1
                print(f"FAIL  {name}\n{error}")
    return 1 if failed else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--legacy"]:
        run_legacy(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(_run_all())


def test_the_editor_changes_all_games_or_one_games_own_items(tmp_path, monkeypatch) -> None:
    from core import controls, paths
    from core import settings as settings_module

    monkeypatch.setattr(paths, "USER_DIR", tmp_path)
    file = tmp_path / "launcher.json"
    file.write_text('{"game": "u1"}', encoding="utf-8")
    editor = settings_module.Editor(file)
    editor.set_control(controls.ALL, "mouse_sens", "1.5")
    editor.bind(controls.ALL, "square", 0, "key:G")
    config = editor.load()
    assert [config.game(key)["mouse_sens"] for key in ("u1", "u2", "u3")] == ["1.5", "1.5", "1.5"]
    assert all("square=G" in (tmp_path / f"probe-{key}.ini").read_text(encoding="utf-8") for key in ("u1", "u2", "u3"))
    # One game's change is its own; the released launcher's per-game call does the same.
    editor.set("u3", "mouse_sens", "0.5")
    editor.bind_pad("u3", "cross", "b")
    config = editor.load()
    assert config.game("u1")["mouse_sens"] == "1.5" and config.game("u3")["mouse_sens"] == "0.5"
    summary = {game["key"]: game for game in editor.own_summary(config)}
    # Three own items: the sensitivity, Cross on B, and Circle, which took Cross's old A (a button does one thing).
    assert summary["u3"]["ownCount"] == 3 and summary["u1"]["ownCount"] == 0
    assert "Mouse sensitivity" in summary["u3"]["ownText"]
    assert editor.control_values("u3")["mouse_sens"] == "0.5"
    assert editor.control_values(controls.ALL)["mouse_sens"] == "1.5"
    # Back to ALL GAMES, item by item or all at once.
    editor.clear_own("u3", controls.Item("setting", "mouse_sens"))
    assert editor.load().game("u3")["mouse_sens"] == "1.5"
    editor.clear_own("u3")
    assert editor.own_summary()[2]["ownCount"] == 0


def test_a_games_keys_can_become_the_all_games_keys(tmp_path, monkeypatch) -> None:
    from core import controls, paths
    from core import settings as settings_module

    monkeypatch.setattr(paths, "USER_DIR", tmp_path)
    file = tmp_path / "launcher.json"
    file.write_text('{"game": "u1"}', encoding="utf-8")
    editor = settings_module.Editor(file)
    editor.bind("u2", "r1", 0, "key:E")
    editor.make_shared("u2")
    assert editor.control_set(controls.ALL).bindings["r1"][0] == "key:E"
    assert editor.control_set("u1").bindings["r1"][0] == "key:E"
    assert editor.own_summary()[1]["ownCount"] == 0


ORIGINAL = {"en-US": "2", "fr": "3", "de": "5", "en-GB": "7"}       # what an untranslated copy holds (part)
TRANSLATED = {"ar": "2", "fr": "3", "de": "5", "en-GB": "7"}        # the Arabic translation took English (US)'s file


def _fake_tool(results: dict[str, Any], calls: list[tuple[Path, str, Path]]) -> Any:
    """A stand-in for tools/text_languages.py: cached_text_languages records its calls and answers per game (a
    {language: file} table, or an exception to raise)."""
    import types

    def cached_text_languages(root: Path, key: str, cache: Path) -> dict[str, str]:
        calls.append((Path(root), key, Path(cache)))
        answer = results.get(key, {})
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return types.SimpleNamespace(cached_text_languages=cached_text_languages,
                                 DATA_DIRS={"u1": "u1data", "u2": "u2data", "u3": "u3data"})


def test_languages_are_read_from_the_texts_the_engine_gets(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "USER_DIR", tmp_path / "user")
    config = cfg.Config.load(_prepare(tmp_path, "u1"))
    # The update beside the game folder holds Uncharted 2's texts: those count for U2, the game's for the others.
    update = tmp_path / "game-patch" / "uroot"
    (update / "sce_sys").mkdir(parents=True)
    (update / "eboot.bin").write_bytes(b"")
    (update / "sce_sys" / "param.sfo").write_bytes(b"")
    (update / "u2data" / "build" / "main").mkdir(parents=True)
    (update / "u2data" / "build" / "main" / "core.psarc").write_bytes(b"")
    calls: list[tuple[Path, str, Path]] = []
    tool = _fake_tool({"u1": TRANSLATED, "u2": ORIGINAL, "u3": ValueError("not a PSARC")}, calls)
    monkeypatch.setattr(settings, "text_languages_tool", lambda: tool)
    lines: list[str] = []
    held = settings.copy_languages(config, log=lines.append)
    assert held == {"u1": TRANSLATED, "u2": ORIGINAL, "u3": {}}
    assert settings.arabic_available(held) == {"u1": True, "u2": False, "u3": False}
    assert [(root, key) for root, key, _ in calls] == [(config.game_dir(), "u1"), (update, "u2"),
                                                       (config.game_dir(), "u3")]
    assert {cache for _, _, cache in calls} == {tmp_path / "user" / "text-languages.json"}
    assert lines == ["Languages: Uncharted 3: Drake's Deception: the texts could not be read (not a PSARC)"]


def test_languages_are_not_looked_for_without_a_game_folder(tmp_path, monkeypatch) -> None:
    file = tmp_path / "launcher.json"
    file.write_text(json.dumps({"game_dir": str(tmp_path / "nowhere")}), encoding="utf-8")
    calls: list[tuple[Path, str, Path]] = []
    monkeypatch.setattr(settings, "text_languages_tool", lambda: _fake_tool({}, calls))
    assert settings.copy_languages(cfg.Config.load(file)) == {"u1": {}, "u2": {}, "u3": {}}
    assert calls == []


def test_the_list_holds_what_the_copy_holds(tmp_path, monkeypatch) -> None:
    import pytest

    monkeypatch.setattr(paths, "USER_DIR", tmp_path / "user")
    file = _prepare(tmp_path, "u1")
    editor = settings.Editor(file, arabic={"u1": True, "u2": False, "u3": False})
    editor.languages = {"u1": TRANSLATED, "u2": ORIGINAL, "u3": ORIGINAL}
    translated = dict(editor.options("u1", "language"))
    assert list(translated)[:1] == ["ar"]                      # Arabic first
    assert "1" not in translated and "18" in translated       # it took English (US)'s place
    assert "2" in translated and "4" in translated             # French, German
    assert "3" not in translated                               # Spanish: not in this (made-up) copy
    original = dict(editor.options("u2", "language"))
    assert "ar" not in original and "1" in original and "18" in original
    with pytest.raises(ValueError, match="Language: no choice 'ar'"):
        editor.set("u2", "language", "ar")
    editor.set("u1", "language", "ar")
    assert editor.values("u1")["language"] == "ar"
    # English (US) on a copy whose translation took its file: English (UK), the real English text.
    editor.set("u2", "language", "1")
    editor.languages = {"u1": TRANSLATED, "u2": TRANSLATED, "u3": ORIGINAL}
    editor.arabic = settings.arabic_available(editor.languages)
    editor.follow_arabic()
    assert editor.values("u2")["language"] == "18"
    assert editor.values("u1")["language"] == "ar"
    # Not read yet: every language may be chosen.
    assert "ar" in dict(settings.Editor(file).options("u3", "language"))


def test_arabic_goes_and_comes_back_with_the_game_folder(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(paths, "USER_DIR", tmp_path / "user")
    file = tmp_path / "launcher.json"
    file.write_text(json.dumps({"games": {"u1": {"language": "ar"}, "u2": {"language": "ar"}}}), encoding="utf-8")
    editor = settings.Editor(file, arabic={"u1": False, "u2": False, "u3": False})   # an English copy
    assert editor.follow_arabic() == (["u1", "u2"], [])
    assert editor.values("u1")["language"] == "1"
    editor.set("u2", "language", "4")                                               # the player picks German
    editor.arabic = {"u1": True, "u2": True, "u3": True}                            # back on the Arabic copy
    assert editor.follow_arabic() == ([], ["u1"])
    assert editor.values("u1")["language"] == "ar" and editor.values("u2")["language"] == "4"


