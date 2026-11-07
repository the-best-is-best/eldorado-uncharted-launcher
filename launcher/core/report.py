# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""A problem report: the logs and settings a crash or a wrong picture is found from, in one zip on the Desktop that the
player attaches to an issue (Settings > LAUNCHER > Problem report). Nothing of the game itself and no saves."""
from __future__ import annotations

import os
import platform
import time
import zipfile
from pathlib import Path

from . import paths

ATTEMPTS = 3  # the last runs' engine logs (analysis/uncharted/attempts/boot-*/boot.log)
LARGEST = 32 * 1024 * 1024  # a log over this is cut to its end (a runaway log would make the zip unsendable)


def desktop() -> Path:
    """The player's Desktop (OneDrive's when Windows keeps it there), else their home folder."""
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    for folder in (home / "OneDrive" / "Desktop", home / "Desktop"):
        if folder.is_dir():
            return folder
    return home


def files(root: Path, user_dir: Path, config_file: Path) -> list[tuple[Path, str]]:
    """(file, name in the zip) for everything a report holds that exists now."""
    found: list[tuple[Path, str]] = []

    def add(path: Path, name: str) -> None:
        if path.is_file():
            found.append((path, name))

    analysis = root / "analysis"
    add(analysis / "uncharted" / "boot.log", "boot.log")
    add(analysis / "uncharted" / "boot.json", "boot.json")
    attempts = sorted((analysis / "uncharted" / "attempts").glob("boot-*/boot.log"),
                      key=lambda path: path.stat().st_mtime, reverse=True)[:ATTEMPTS]
    for number, log in enumerate(attempts, 1):
        add(log, f"attempts/{number}-{log.parent.name}.log")
    add(user_dir / "launcher-last-run.log", "launcher-last-run.log")
    for pattern in ("probe-u*.ini", "input-u*.ini", "bbport-u*.ini", "test-env.txt", "key-labels.txt"):
        for path in sorted(user_dir.glob(pattern)):
            add(path, f"settings/{path.name}")
    for path in sorted((analysis / "uncharted").glob("hang-*.txt"))[-3:]:
        add(path, f"hangs/{path.name}")
    add(config_file, "settings/launcher.json")
    add(root / "tools" / "VERSION", "VERSION")
    return found


def write(target_folder: Path | None = None, root: Path | None = None, user_dir: Path | None = None,
          config_file: Path | None = None) -> Path:
    """The zip, named by the time; returns its path. Raises OSError when it cannot be written."""
    root = root or paths.ROOT
    user_dir = user_dir or paths.USER_DIR
    config_file = config_file or paths.config_file()
    folder = target_folder or desktop()
    target = folder / f"El Dorado report {time.strftime('%Y-%m-%d %H-%M')}.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("system.txt", f"Windows {platform.version()} ({platform.machine()})\n"
                                       f"Made {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        for path, name in files(root, user_dir, config_file):
            data = path.read_bytes()
            if len(data) > LARGEST:
                data = b"(the start of this log was left out: too large)\n" + data[-LARGEST:]
            archive.writestr(name, data)
    return target
