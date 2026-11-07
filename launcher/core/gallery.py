# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The player's screenshots: the engine saves F12 shots to USER/screenshots/<key>/. Open one, open the folder, or
move one to the Windows Recycle Bin (never deleted outright, so a mistake can be undone)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from . import paths

PICTURE_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg")


class GalleryError(Exception):
    """A screenshot or the folder could not be opened or moved to the Recycle Bin."""


@dataclass(frozen=True)
class Shot:
    path: Path
    taken: float  # file time (seconds since 1970)

    @property
    def name(self) -> str:
        return self.path.name

    def label(self) -> str:
        """When it was taken: from the engine's file name (YYYYmmdd-HHMMSS, kept when copied), else the file time."""
        try:
            when = time.strptime(self.path.stem, "%Y%m%d-%H%M%S")
        except ValueError:
            when = time.localtime(self.taken)
        return time.strftime("%d %b %Y  %H:%M", when)


def folder(key: str, user_dir: Path | None = None) -> Path:
    return (user_dir or paths.USER_DIR) / "screenshots" / key


def shots(key: str, user_dir: Path | None = None) -> list[Shot]:
    """The game's screenshots, newest first; none when the folder is not there yet."""
    try:
        found = [Shot(entry, entry.stat().st_mtime) for entry in folder(key, user_dir).iterdir()
                 if entry.suffix.lower() in PICTURE_SUFFIXES and entry.is_file()]
    except FileNotFoundError:
        return []
    except OSError as error:
        raise GalleryError(f"the screenshots folder could not be read ({error})") from error
    return sorted(found, key=lambda shot: shot.taken, reverse=True)


def open_path(path: Path) -> None:
    """Opens a picture or a folder with the program Windows has for it."""
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]  # Windows only, as the launcher
    except (OSError, AttributeError) as error:
        raise GalleryError(f"{path} could not be opened ({error})") from error


def open_folder(key: str, user_dir: Path | None = None) -> Path:
    """Opens the game's screenshots folder (made first, so it opens before the first F12)."""
    target = folder(key, user_dir)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise GalleryError(f"{target} could not be made ({error})") from error
    open_path(target)
    return target


def recycle(path: Path) -> None:
    """Moves a file to the Recycle Bin with the shell's file operation (FO_DELETE with FOF_ALLOWUNDO)."""
    if os.name != "nt":
        raise GalleryError("the Recycle Bin is only on Windows")
    import ctypes
    from ctypes import wintypes

    class FileOperation(ctypes.Structure):  # SHFILEOPSTRUCTW
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", wintypes.WORD), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", wintypes.LPVOID), ("lpszProgressTitle", wintypes.LPCWSTR)]

    fo_delete = 0x3
    flags = 0x40 | 0x10 | 0x400 | 0x4  # FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_NOERRORUI, FOF_SILENT
    # pFrom is a list ended by two NULs; the shell wants a full path.
    operation = FileOperation(None, fo_delete, str(Path(path).resolve()) + "\0", None, flags, False, None, None)
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if code or operation.fAnyOperationsAborted:
        raise GalleryError(f"{Path(path).name} could not be moved to the Recycle Bin (code {code})")


def delete(shot: Shot) -> None:
    """A screenshot to the Recycle Bin; it must still be the file the player saw."""
    if not shot.path.is_file():
        raise GalleryError(f"{shot.name} is not there any more")
    recycle(shot.path)
