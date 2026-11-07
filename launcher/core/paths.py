# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Where the launcher's files live. One place, so no module builds a path of its own."""
from __future__ import annotations

import os
from pathlib import Path

# The package folder: launcher/ sits next to tools/, gow3_pc/ and analysis/.
ROOT: Path = Path(__file__).resolve().parents[2]
LAUNCHER_DIR: Path = ROOT / "launcher"
USER_DIR: Path = ROOT / "analysis" / "uncharted-user"

APP_NAME = "El Dorado Launcher"
# The taskbar groups the launcher's windows under this id (the same id as the released launcher, so pinned
# shortcuts keep working across the switch).
APP_ID = "ElDorado.Uncharted.Launcher"


def config_dir() -> Path:
    """The folder that holds launcher.json (%APPDATA%\\El Dorado Launcher, as the released launcher)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def config_file() -> Path:
    return config_dir() / "launcher.json"
