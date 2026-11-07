# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The problem report's zip and the launcher's STOP (a request file first, the game ended only after a wait)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import launch, report  # noqa: E402


def test_report_holds_logs_and_settings_only(tmp_path) -> None:
    root, user = tmp_path / "port", tmp_path / "port" / "analysis" / "uncharted-user"
    attempts = root / "analysis" / "uncharted" / "attempts"
    for number in range(5):
        log = attempts / f"boot-{number}" / "boot.log"
        log.parent.mkdir(parents=True)
        log.write_bytes(f"run {number}\n".encode())
        os.utime(log, (1000 + number, 1000 + number))
    (root / "analysis" / "uncharted" / "boot.log").write_bytes(b"latest\n")
    user.mkdir(parents=True)
    (user / "launcher-last-run.log").write_text("start\n", encoding="utf-8")
    (user / "probe-u1.ini").write_text("[x]\n", encoding="utf-8")
    (user / "savedata").mkdir()
    (user / "savedata" / "SAVEDATA0100.bin").write_bytes(b"save")  # never in a report
    config = tmp_path / "launcher.json"
    config.write_text("{}", encoding="utf-8")
    target = report.write(tmp_path, root=root, user_dir=user, config_file=config)
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        assert archive.read("boot.log") == b"latest\n"
        assert archive.read("attempts/1-boot-4.log") == b"run 4\n"  # the newest runs, newest first
    assert {"system.txt", "launcher-last-run.log", "settings/probe-u1.ini", "settings/launcher.json"} <= names
    assert len([name for name in names if name.startswith("attempts/")]) == report.ATTEMPTS
    assert not any("savedata" in name.lower() for name in names)


class _Process:
    """A stand-in for the start script's process: ends when told, or never."""

    def __init__(self, ends_after: float | None) -> None:
        self.ends_at = None if ends_after is None else time.monotonic() + ends_after
        self.pid = 4242

    def poll(self):
        return 0 if self.ends_at is not None and time.monotonic() >= self.ends_at else None

    def wait(self, timeout=None):
        if self.ends_at is None or (timeout is not None and time.monotonic() + timeout < self.ends_at):
            if timeout is not None:
                time.sleep(timeout)
            raise subprocess.TimeoutExpired("probe", timeout)
        time.sleep(max(0.0, self.ends_at - time.monotonic()))
        return 0


def _session(process: _Process, prepare: bool) -> launch.Session:
    session = launch.Session.__new__(launch.Session)
    session.process, session.prepare = process, prepare
    return session


def test_stop_asks_first_and_ends_only_a_game_that_stays(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(launch, "STOP_FILE", tmp_path / "stop-request")
    monkeypatch.setattr(launch, "STOP_WAIT", 0.3)
    kills: list[list[str]] = []
    monkeypatch.setattr(launch.subprocess, "run", lambda args, **_: kills.append(args))
    # The game closes by itself after the request: no kill, and the request is gone afterwards.
    _session(_Process(0.1), prepare=False).stop()
    assert (tmp_path / "stop-request").exists()
    time.sleep(0.5)
    assert kills == [] and not (tmp_path / "stop-request").exists()
    # A game that does not close is ended after the wait.
    _session(_Process(None), prepare=False).stop()
    time.sleep(0.6)
    assert len(kills) == 1 and kills[0][:2] == ["taskkill", "/PID"]
    # Preparing shaders has no window to close: ended at once, no request written.
    kills.clear()
    _session(_Process(None), prepare=True).stop()
    time.sleep(0.15)
    assert len(kills) == 1 and not (tmp_path / "stop-request").exists()
