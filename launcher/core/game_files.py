# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The player's game files and folders: the game folder (chosen, or the player's own game .pkg unpacked by
tools/install_update.py), the game update (a folder or its .pkg, the same tool), the files check
(tools/check_game_files.py), the shader cache, the folders the settings open, and resetting the settings. The
package ships no game file; everything here works on the player's own copy."""
from __future__ import annotations

import importlib.util
import shutil
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from . import config as cfg
from . import games, paths

TOOLS = paths.ROOT / "tools"
SHADER_CACHE = paths.USER_DIR / "cache"
# The game update next to the game folder, found as tools/probe_uncharted.py finds it.
UPDATE_SUFFIXES = ("-patch", "-update", "_patch", "_update")
# Each game's own log folder under analysis/ (the start script's names).
LOG_FOLDERS = ("uncharted", "big2-ps4_Shipping", "big3-ps4_Shipping")


class GameFilesError(Exception):
    """Something the player has to fix; the message says what."""


def tool_module(name: str) -> ModuleType:
    """tools/<name>.py loaded by path: the scripts the released launcher used (each also runs on its own)."""
    script = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script) if script.is_file() else None
    if spec is None or spec.loader is None:
        raise GameFilesError(f"A launcher tool is missing (reinstall the launcher):\n{script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class FileCheck:
    root: Path
    total: int
    missing: list[str]
    wrong_size: list[str]

    @property
    def complete(self) -> bool:
        return not self.missing and not self.wrong_size

    def summary(self, shown: int = 15) -> str:
        head = (f"{self.total} files checked, {len(self.missing)} missing, {len(self.wrong_size)} with a wrong size.")
        if self.complete:
            return "Your game files are complete.\n\n" + head
        problems = [f"missing  {name}" for name in self.missing] + [f"size     {name}" for name in self.wrong_size]
        listed = "\n".join(problems[:shown])
        if len(problems) > shown:
            listed += f"\n... and {len(problems) - shown} more"
        return ("Your game files are incomplete, so the game will stop where it needs them. Extract or dump the "
                f"base game again.\n\n{head}\n\n{listed}")


# --- param.sfo ----------------------------------------------------------------------------------------------------

def sfo_values(folder: Path) -> dict[str, str]:
    """The text values of a game folder's sce_sys/param.sfo ({} when it cannot be read)."""
    try:
        data = (folder / "sce_sys" / "param.sfo").read_bytes()
        _, _, keys_at, values_at, count = struct.unpack_from("<IIIII", data)
        values = {}
        for index in range(count):
            key_at, _, length, _, value_at = struct.unpack_from("<HHIII", data, 20 + index * 16)
            start = keys_at + key_at
            key = data[start:data.index(b"\0", start)].decode("utf-8", "replace")
            raw = data[values_at + value_at:values_at + value_at + length]
            values[key] = raw.rstrip(b"\0").decode("utf-8", "replace")
        return values
    except (OSError, struct.error, ValueError):
        return {}


def app_version(folder: Path) -> str:
    return sfo_values(folder).get("APP_VER", "")


# --- the game folder ----------------------------------------------------------------------------------------------

def set_game_dir(config: cfg.Config, folder: Path) -> Path:
    """Remembers the game folder (or its uroot) after checking it is the Collection's."""
    for candidate in (folder, folder / "uroot"):
        if games.is_game_dir(candidate):
            config.data["game_dir"] = str(candidate)
            config.save()
            return candidate
    raise GameFilesError("That folder has no eboot.bin and sce_sys\\param.sfo.\n\n"
                         "Choose the game's own folder (CUSA02344 or CUSA02320, or its uroot).")


def _require_game_dir(config: cfg.Config) -> Path:
    game_dir = config.game_dir()
    if not games.is_game_dir(game_dir):
        raise GameFilesError("Choose the game folder first.")
    return game_dir


# --- the game update ----------------------------------------------------------------------------------------------

def _title_folder(game_dir: Path) -> Path:
    return game_dir.parent if game_dir.name.lower() == "uroot" else game_dir


def update_next_to_game(game_dir: Path) -> Path | None:
    """<game folder>-patch (or -update) beside the game folder, with or without uroot."""
    title = _title_folder(game_dir)
    names = {title.name.lower() + suffix for suffix in UPDATE_SUFFIXES}
    try:
        neighbours = list(title.parent.iterdir())
    except OSError:
        return None
    for entry in neighbours:
        if entry.name.lower() in names:
            for candidate in (entry / "uroot", entry):
                if games.is_game_dir(candidate):
                    return candidate
    return None


def update_in_use(config: cfg.Config) -> Path | None:
    """The update the games get: the chosen folder, else one beside the game folder."""
    return config.chosen_update() or update_next_to_game(config.game_dir())


def update_text(config: cfg.Config) -> str:
    update = update_in_use(config)
    if update:
        return f"Game update {app_version(update) or '?'} is used: {update}"
    version = app_version(config.game_dir())
    if version and version >= "01.02":
        return f"Game version {version} (the update is in the game folder)."
    return (f"Game version {version or '?'}, no update found. For the 1.02 fixes choose your update 1.02 folder "
            "or its .pkg.")


def _installer() -> ModuleType:
    """tools/install_update.py: unpacks the player's own update or game .pkg (PkgTool)."""
    return tool_module("install_update")


def set_update_folder(config: cfg.Config, folder: Path) -> Path:
    """An update the player already extracted, anywhere: checked and remembered (nothing is copied)."""
    game_dir = _require_game_dir(config)
    installer = _installer()
    try:
        update = Path(installer.check_folder(folder, game_dir))
    except installer.UpdateError as error:
        raise GameFilesError(f"This folder can't be used:\n{error}") from error
    config.data["update_dir"] = str(update)
    config.save()
    return update


def existing_update(config: cfg.Config) -> Path | None:
    """The update folder an install from .pkg would replace."""
    game_dir = config.game_dir()
    if not games.is_game_dir(game_dir):
        return None
    found = _installer().existing_update(game_dir)
    return Path(found) if found else None


def install_update_pkg(config: cfg.Config, pkg: Path, log: Callable[[str], None]) -> Path:
    """The player's update .pkg unpacked beside the game folder as <game folder>-patch; used from then on."""
    game_dir = _require_game_dir(config)
    installer = _installer()
    try:
        update = Path(installer.install(pkg, game_dir, log=log))
    except installer.UpdateError as error:
        raise GameFilesError(f"The update was not installed:\n{error}") from error
    except OSError as error:  # a disk or permission problem: shown as it is
        raise GameFilesError(f"The update was not installed:\n{type(error).__name__}: {error}") from error
    # Reloaded: the install takes minutes, the other settings may have changed meanwhile.
    fresh = cfg.Config.load(config.file)
    fresh.data["update_dir"] = str(update)
    fresh.save()
    config.data["update_dir"] = str(update)
    return update


def install_game_pkg(config: cfg.Config, pkg: Path, destination: Path, log: Callable[[str], None]) -> Path:
    """The player's own game .pkg unpacked into <destination>\\<title id> (tools/install_update.py install_game,
    which adds the metadata the launcher needs); its uroot is the game folder from then on."""
    installer = _installer()
    try:
        unpacked = Path(installer.install_game(pkg, destination, log=log))
    except installer.UpdateError as error:
        raise GameFilesError(f"The game was not installed:\n{error}") from error
    except OSError as error:  # a disk or permission problem: shown as it is
        raise GameFilesError(f"The game was not installed:\n{type(error).__name__}: {error}") from error
    if not games.is_game_dir(unpacked):
        raise GameFilesError(f"The game was unpacked, but {unpacked} has no eboot.bin and sce_sys\\param.sfo.")
    # Reloaded as for an update: the unpacking takes minutes.
    fresh = cfg.Config.load(config.file)
    game_dir = set_game_dir(fresh, unpacked)
    config.data["game_dir"] = fresh.data["game_dir"]
    return game_dir


# --- check files, shader cache ------------------------------------------------------------------------------------

def check_files(game_dir: Path) -> FileCheck:
    """Every base game file there with the right size (tools/check_game_files.py: names and sizes only)."""
    checker = tool_module("check_game_files")
    try:
        root, total, missing, wrong = checker.check(game_dir)
    except OSError as error:
        raise GameFilesError(f"The check could not run:\n{error}") from error
    return FileCheck(Path(root), int(total), list(missing), list(wrong))


def clear_shader_cache(cache: Path = SHADER_CACHE) -> bool:
    """Deletes the compiled shaders (they are made again while playing). False when there is no cache."""
    if not cache.exists():
        return False
    try:
        shutil.rmtree(cache)
    except OSError as error:
        raise GameFilesError(f"The shader cache could not be deleted (is the game running?):\n{error}") from error
    return True


# --- folders and reset --------------------------------------------------------------------------------------------

def latest_log_folder() -> Path:
    """The folder of the newest boot.log, else analysis\\."""
    logs = [paths.ROOT / "analysis" / name / "boot.log" for name in LOG_FOLDERS]
    found = [log for log in logs if log.is_file()]
    if not found:
        return paths.ROOT / "analysis"
    return max(found, key=lambda log: log.stat().st_mtime).parent


def player_folder(name: str) -> Path:
    """"logs", "saves" or "screenshots": the folder to open (its parent when it does not exist yet)."""
    if name == "logs":
        return latest_log_folder()
    if name == "saves":
        folder = paths.USER_DIR / "savedata"
    elif name == "screenshots":
        folder = paths.USER_DIR / "screenshots"
    else:
        raise GameFilesError(f"No such folder: {name}")
    return folder if folder.is_dir() else paths.USER_DIR


def reset_settings(config: cfg.Config) -> None:
    """Every game back to its defaults (launcher.json and probe-uN.ini); the game folder, the update and the
    controls written by the in-game menu stay."""
    kept = {key: config.data.get(key) for key in ("game", "game_dir", "update_dir")}
    for key, value in cfg.LAUNCHER_DEFAULTS.items():
        config.data[key] = value
    config.data.update({key: value for key, value in kept.items() if value is not None})
    for name in cfg.CHEATS:
        config.data.pop("cheat_" + name, None)
    for key in games.KEYS:
        config.data["games"][key] = dict(cfg.GAME_DEFAULTS)
        cfg.write_ini(key, dict(cfg.INI_DEFAULTS))
    config.save()
