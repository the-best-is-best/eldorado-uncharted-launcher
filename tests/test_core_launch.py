# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import config, games, launch, resolution  # noqa: E402


def test_sizes_with_and_without_upscaling() -> None:
    game = {"resolution": "1920x1080", "aspect": "16:9", "upscale": "quality"}
    assert resolution.sizes(game, {"upscaler": "dlss"}) == ("1280x720", "1920x1080")
    assert resolution.sizes(game, {"upscaler": "off", "fsr1": "0"}) == ("1920x1080", None)
    assert resolution.at_aspect("2560x1440", "21:9") == "3440x1440"
    assert resolution.at_aspect("1280x720", "16:10") == "1280x800"


def test_environment_has_every_games_own_settings(tmp_path: Path) -> None:
    file = tmp_path / "launcher.json"
    file.write_text('{"game": "u2", "games": {"u3": {"language": "ar"}}, "cheat_ammo": true}', encoding="utf-8")
    env = launch.environment(config.Config.load(file), {})
    assert env["UNCHARTED_LANGUAGE_U3"] == "ar"
    assert env["UNCHARTED_LANGUAGE_U1"] == "1"
    assert env["UNCHARTED_CHEATS"] == "ammo"
    for key in games.KEYS:
        assert f"UNCHARTED_RESOLUTION_{key.upper()}" in env


def test_environment_language_is_the_started_games(tmp_path: Path) -> None:
    file = tmp_path / "launcher.json"
    file.write_text('{"game": "u1", "games": {"u1": {"language": "4"}, "u3": {"language": "ar"}}}',
                    encoding="utf-8")
    loaded = config.Config.load(file)
    assert launch.environment(loaded, {})["UNCHARTED_LANGUAGE"] == "4"  # the chosen game's
    assert launch.environment(loaded, {}, games.by_key("u3"))["UNCHARTED_LANGUAGE"] == "ar"  # a shortcut's --play


def test_command_is_the_released_launchers() -> None:
    args = launch.command(games.by_key("u3"), Path("D:/Game"))
    assert args[2:] == [str(launch.RUN_SCRIPT), "--boot", "--seconds", "0", "--executable",
                        "big3-ps4_Shipping.elf", "--game", str(Path("D:/Game"))]


def test_switched_game_from_the_start_scripts_line() -> None:
    assert launch.switched_game("Collection: switching to big2-ps4_Shipping.elf") == games.by_key("u2")
    assert launch.switched_game("Collection: switching to eboot.bin (restart)") == games.by_key("u1")
    assert launch.switched_game("Collection: switching to ") is None
    assert launch.switched_game("Collection: switching to other.elf") is None
    assert launch.switched_game("Starting Uncharted 2") is None


def test_crash_reason_freeze_fault_and_stop() -> None:
    assert launch.crash_reason(["Frame stats: 60 fps", "Freeze: no new frame for 12 s"]).startswith(
        "The game froze (no new frame for 12 s)")
    assert "C:\\logs\\hang.txt" in launch.crash_reason(["Hang watchdog: report C:\\logs\\hang.txt"])
    fault = launch.crash_reason(["Fault: access violation at 0x1234", "  host #0 vk_rasterizer.cpp:10", "more"])
    assert fault.startswith("Fault: access violation at 0x1234\nhost #0 vk_rasterizer.cpp:10")
    assert "boot.log" in fault
    stop = launch.crash_reason(["one", "two", "STOP: out of memory", "after"])
    assert stop == "one\ntwo\nSTOP: out of memory"
    assert launch.crash_reason(["Frame stats: 60 fps", "exit 0"]) == ""
    # A freeze counts however the run ended afterwards.
    assert launch.crash_reason(["Freeze: no new frame for 9 s", "STOP: closed"]).startswith("The game froze")


def test_last_run_reason_prefers_this_runs_engine_log(tmp_path: Path) -> None:
    engine_log = tmp_path / "boot.log"
    run_log = tmp_path / "launcher-last-run.log"
    engine_log.write_text("Frame stats\nFault: bad read\n#0 somewhere\n", encoding="utf-8")
    run_log.write_text(f"2026-11-07 start\nLog: {engine_log}\nSTOP: script stop\n", encoding="utf-8")
    now = time.time()
    assert launch.last_run_reason(now - 60, run_log).startswith("Fault: bad read\n#0 somewhere")
    # An engine log older than this run says nothing about it: the script's own output answers.
    assert launch.last_run_reason(now + 3600, run_log) == "2026-11-07 start\nLog: " + str(engine_log) + \
        "\nSTOP: script stop"
    assert launch.last_run_reason(now, tmp_path / "missing.log") == ""
    assert launch.tail(tmp_path / "missing.log") == []
    assert launch.named_log(["Log: C:\\x\\boot.log", "later"]) == Path("C:\\x\\boot.log")
    assert launch.named_log(["nothing"]) is None
