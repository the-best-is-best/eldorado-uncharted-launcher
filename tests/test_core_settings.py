# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Settings screen's core: GPU classes, presets, bindings, the editor's scopes and the game languages.

usage: python tests/test_core_settings.py        runs every test (pytest finds them too)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "launcher"))

from core import config as cfg  # noqa: E402
from core import games, gpu, input_map, launch, paths, presets, settings  # noqa: E402


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


# --- tests --------------------------------------------------------------------------------------------------------

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


