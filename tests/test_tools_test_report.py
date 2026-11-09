# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""tools/test_report.py reads the game's logs into the test list; the launcher warns about Uncharted 2 above 60."""
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "launcher"))

import test_report  # noqa: E402


def run(root: Path, n: int, game: str, body: str, exit_code: int = 0, seconds: float = 600) -> None:
    log = {"u1": "uncharted", "u2": "big2-ps4_Shipping", "u3": "big3-ps4_Shipping"}[game]
    folder = root / "analysis" / log / "attempts" / f"boot-{n}"
    folder.mkdir(parents=True)
    exe = test_report.EXECUTABLES[game]
    (folder / "boot.log").write_text(f"# 2026-11-09 18:0{n}:00 {exe} ({game}) from x\n{body}\n", encoding="utf-8")
    (folder / "boot.json").write_text(json.dumps({"exit_code": exit_code, "elapsed_seconds": seconds}))


def statuses(root: Path) -> dict[str, str]:
    runs = test_report.read_runs(root, None)
    return {item.id: item.check(runs, root).status for item in test_report.ITEMS}


def test_nothing_played_is_not_tried(tmp_path) -> None:
    assert set(statuses(tmp_path).values()) == {test_report.NOT_TRIED}


def test_the_logs_say_what_ran_and_how_it_ended(tmp_path) -> None:
    run(tmp_path, 1, "u1", "Mouse: the turn-the-stick prompt is on screen: the mouse turns the left stick\n"
                           "Mouse: the turn-the-stick prompt went away while the mouse turned the stick (done)\n"
                           "Pad: walk key pressed: Nate walks\nPad: walk key pressed: Nate runs\n"
                           "Window: Alt+Enter, fullscreen\n"
                           "Unlock all rewards: item check, id check patched", seconds=300)
    run(tmp_path, 2, "u3", "Mouse: Uncharted 3 follow camera turned in its input function\n"
                           "Frame pacing: median 16.7 ms, frames over 25/33/50 ms: 4/2/1", seconds=300)
    got = statuses(tmp_path)
    assert got["wheel_mouse"] == got["walk"] == got["fullscreen_keys"] == got["rewards"] == test_report.PASSED
    assert got["wheel_picture"] == got["mouse_camera"] == test_report.LOOK
    assert got["u3_hitches"] == test_report.INFO
    assert got["crashes"] == test_report.PASSED and got["sound_cuts"] == test_report.NOT_TRIED  # 20 min needed


def test_failures_show(tmp_path) -> None:
    run(tmp_path, 1, "u1", "Mouse: the turn-the-stick prompt is on screen: the mouse turns the left stick")
    run(tmp_path, 2, "u2", "Mouse: Uncharted 2 follow camera turned in its input function\nFile: slow read, 900 ms "
                           "for 65536 bytes (fd 12)\nFault: read access to 0000000200001f31 at bb-probe.exe+0x30b22",
        exit_code=3, seconds=1800)
    got = statuses(tmp_path)
    assert got["wheel_mouse"] == got["mouse_camera"] == got["sound_cuts"] == got["crashes"] == test_report.FAILED


def test_a_mark_wins_and_the_report_is_written(tmp_path) -> None:
    run(tmp_path, 1, "u1", "Mouse: the turn-the-stick prompt is on screen: the mouse turns the left stick")
    test_report.save_mark(tmp_path, "wheel_picture", "ok", "looks right")
    text = test_report.report(tmp_path, None)
    assert "| U1 wheel prompt shows the mouse going round (`wheel_picture`) | **PASSED** | marked" in text


def test_the_triangle_prompt_is_found_among_the_captured_pictures(tmp_path) -> None:
    folder = tmp_path / "dumps"
    folder.mkdir()
    green = struct.pack("<HHI", (6 << 11) | (54 << 5) | 13, 0, 0)  # BC1 block, colour 0 about (55, 216, 104)
    dark = struct.pack("<HHI", (3 << 11) | (6 << 5) | 3, 0, 0)
    (folder / "aa-512x512-bc1-13.bin").write_bytes(green * 2000 + dark * 30768)
    (folder / "bb-512x512-bc1-13.bin").write_bytes(dark * 32768)
    found = test_report.triangle_dumps(folder)
    assert [path.name for path, _ in found] == ["aa-512x512-bc1-13.bin"]


@pytest.mark.parametrize("game,fps,warned", [("u2", "120", True), ("u2", "60", False), ("u3", "120", False)])
def test_uncharted_2_above_60_is_warned_about(monkeypatch, game, fps, warned) -> None:
    from ui import settings_model
    monkeypatch.setattr(settings_model, "QGuiApplication", SimpleNamespace(primaryScreen=lambda: None))
    fake = SimpleNamespace(_game=game, _setting_rows=lambda tab, config, values: [{"kind": "choice"}])
    rows = settings_model.SettingsModel._performance_rows(fake, None, {"fps_limit": fps})
    texts = [row.get("text", "") for row in rows]
    assert any("Uncharted 2 above 60 FPS" in text for text in texts) == warned
