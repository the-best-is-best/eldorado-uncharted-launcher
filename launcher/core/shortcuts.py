# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Desktop shortcuts: one to the launcher, one per game (started with --play <key>).

A game's shortcut gets that game's icon, made on the player's PC from their own copy: the Collection's
sce_sys/trophy/trophy0N.trp packs each hold the game's ICON0.PNG. The package ships no game picture; the icons are
written to analysis/uncharted-user/icons/uN.ico. A TRP pack is a big-endian header (magic 0xDCA24D00, file count at
16, entry size at 20) and from 0x60 one entry per file: a 32-byte name, its offset and size (64-bit).
"""
from __future__ import annotations

import ctypes
import io
import os
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import games, paths

TRP_MAGIC = 0xDCA24D00
ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ICON_DIR = paths.USER_DIR / "icons"
APP_ICON = paths.LAUNCHER_DIR / "ui" / "assets" / "eldorado.ico"
STARTER = paths.ROOT / "Uncharted Launcher.exe"
ENTRY_SCRIPT = paths.LAUNCHER_DIR / "main.py"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ShortcutError(Exception):
    """A shortcut could not be made; the message is for the player."""


@dataclass(frozen=True)
class Shortcut:
    name: str          # the .lnk file's name, without the extension
    description: str
    arguments: str     # after the launcher's own (--play u1)
    icon: Path


# --- the game's icon from its trophy pack ---------------------------------------------------------------------------

def trophy_pack(game_dir: Path, game: games.Game) -> Path:
    return game_dir / "sce_sys" / "trophy" / f"trophy0{game.number}.trp"


def trp_file(pack: Path, wanted: str) -> bytes | None:
    """One file of a TRP pack, or None (no pack, not a pack, no such file)."""
    try:
        with pack.open("rb") as source:
            header = source.read(0x60)
            if len(header) < 0x60 or struct.unpack_from(">I", header, 0)[0] != TRP_MAGIC:
                return None
            count, entry_size = struct.unpack_from(">II", header, 16)
            if not 0 < count < 4096 or not 40 <= entry_size <= 256:
                return None
            table = source.read(count * entry_size)
            for index in range(count):
                entry = table[index * entry_size:(index + 1) * entry_size]
                if entry[:32].split(b"\0")[0].decode("latin-1").upper() != wanted.upper():
                    continue
                offset, size = struct.unpack_from(">QQ", entry, 32)
                if not 0 < size < (8 << 20):
                    return None
                source.seek(offset)
                return source.read(size)
    except (OSError, struct.error):
        return None
    return None


def game_icon(game_dir: Path, game: games.Game, folder: Path = ICON_DIR) -> Path | None:
    """icons/uN.ico from the game's trophy pack (made again when the pack is newer), or None without the pack or
    Pillow (the shortcut then takes El Dorado's icon)."""
    target = folder / f"{game.key}.ico"
    pack = trophy_pack(game_dir, game)
    if not pack.is_file():
        return None
    if target.is_file() and target.stat().st_mtime >= pack.stat().st_mtime:
        return target
    picture = trp_file(pack, "ICON0.PNG")
    if picture is None:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        icon = Image.open(io.BytesIO(picture)).convert("RGBA")
    except (OSError, ValueError):
        return None
    # The 320x176 icon centred on a transparent square, as large as fits.
    square = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    icon.thumbnail((256, 256), Image.LANCZOS)
    square.alpha_composite(icon, ((256 - icon.width) // 2, (256 - icon.height) // 2))
    folder.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    square.save(temporary, format="ICO", sizes=ICON_SIZES)
    os.replace(temporary, target)
    return target


# --- the shortcuts ------------------------------------------------------------------------------------------------

def desktop_folder() -> Path:
    """The player's Desktop as Windows knows it (OneDrive and redirected Desktops move it away from
    %USERPROFILE%\\Desktop)."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                        ("Data4", ctypes.c_ubyte * 8)]

        desktop = GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
        found = ctypes.c_void_p()
        shell32 = ctypes.windll.shell32
        shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                                                 ctypes.POINTER(ctypes.c_void_p)]
        if shell32.SHGetKnownFolderPath(ctypes.byref(desktop), 0, None, ctypes.byref(found)) == 0:
            try:
                folder = Path(ctypes.wstring_at(found.value))
            finally:
                ctypes.windll.ole32.CoTaskMemFree(found)
            if folder.is_dir():
                return folder
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def launcher_command() -> tuple[Path, str]:
    """What starts the launcher: the package's starter, or (source tree) pythonw with main.py."""
    if STARTER.is_file():
        return STARTER, ""
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    return (pythonw if pythonw.is_file() else python), f'"{ENTRY_SCRIPT}"'


def wanted(game_dir: Path) -> list[Shortcut]:
    """The launcher's shortcut and one per game."""
    result = [Shortcut("Uncharted", paths.APP_NAME, "", APP_ICON)]
    for game in games.GAMES:
        icon = game_icon(game_dir, game) or APP_ICON
        result.append(Shortcut(game.name.replace(":", " -"), f"{game.name} (starts directly)",
                               f"--play {game.key}", icon))
    return result


def _ps(value: object) -> str:
    """A PowerShell single-quoted string ("Drake's" doubles the quote)."""
    return "'" + str(value).replace("'", "''") + "'"


def create(shortcut: Shortcut, folder: Path) -> Path:
    """Writes <folder>/<name>.lnk (WScript.Shell through PowerShell: no extra Python package)."""
    target, base = launcher_command()
    link = folder / f"{shortcut.name}.lnk"
    arguments = f"{base} {shortcut.arguments}".strip()
    # Messages in UTF-8: a German or Portuguese Windows answers in its own language.
    script = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
              f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({_ps(link)});"
              f"$s.TargetPath={_ps(target)};$s.Arguments={_ps(arguments)};"
              f"$s.WorkingDirectory={_ps(paths.ROOT)};$s.IconLocation={_ps(shortcut.icon)};"
              f"$s.Description={_ps(shortcut.description)};$s.Save()")
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                creationflags=NO_WINDOW, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise ShortcutError(f"{link.name}: {error}") from error
    if result.returncode != 0:
        raise ShortcutError(f"{link.name}: {result.stderr.strip() or 'PowerShell failed'}")
    return link


def create_all(game_dir: Path, folder: Path | None = None) -> list[Path]:
    """Every shortcut on the Desktop (or `folder`); raises ShortcutError naming each one that failed."""
    folder = folder or desktop_folder()
    made: list[Path] = []
    failed: list[str] = []
    for shortcut in wanted(game_dir):
        try:
            made.append(create(shortcut, folder))
        except ShortcutError as error:
            failed.append(str(error))
    if failed:
        raise ShortcutError("Could not create these shortcuts:\n" + "\n".join(failed))
    return made
