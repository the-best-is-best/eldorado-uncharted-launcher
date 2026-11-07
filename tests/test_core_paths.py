# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import paths  # noqa: E402


def test_root_holds_the_start_script() -> None:
    assert (paths.ROOT / "tools" / "probe_uncharted.py").is_file()


def test_config_file_is_the_released_launchers(monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", "C:\\Users\\player\\AppData\\Roaming")
    assert paths.config_file() == Path("C:\\Users\\player\\AppData\\Roaming") / "El Dorado Launcher" / "launcher.json"
