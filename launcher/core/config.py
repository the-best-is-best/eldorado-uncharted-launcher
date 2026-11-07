# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The launcher's settings (launcher.json, shared with the released launcher) and each game's runtime settings
(analysis/uncharted-user/probe-uN.ini, also written by the in-game menu)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import games, paths, safe_write

# The released launcher's last config version: settings older than it are migrated by that launcher; this one
# reads them as they are and writes back only what it changes.
CONFIG_VERSION = 9

LAUNCHER_DEFAULTS: dict[str, Any] = {"game": "u1", "diagnostics": True, "game_dir": "", "unlock": False,
                                     "job_sleep": "auto", "anisotropy": "0", "no_dof": False,
                                     "torch_forward": True, "u3_exposure": "0", "hires_shadows": False,
                                     "check_updates": True}
# Each game's own launcher settings. The controls (controls .. vibration) are also written into the game's ini,
# where tools/probe_uncharted.py reads them; launcher.json keeps a copy as the released launcher does.
GAME_DEFAULTS: dict[str, Any] = {"preset": "medium", "resolution": "1920x1080", "aspect": "16:9", "upscale": "off",
                                 "multithreaded": True, "save_profile": "1", "language": "1",
                                 "controls": None, "pad_controls": None, "mouse": True, "mouse_sens": "1.0",
                                 "mouse_invert": False, "prompts": "auto", "mouse_aim_sens": "1.0",
                                 "vibration": True,
                                 # The items this game sets apart from the shared controls (core/controls.py).
                                 "own_controls": {}}
INI_DEFAULTS: dict[str, str] = {
    "display_mode": "windowed", "vsync": "1", "fps_limit": "60", "frames_queued": "1", "async_shaders": "1",
    "fsr1": "0", "rcas": "1", "rcas_strength": "75", "show_fps": "1", "upscaler": "off", "frame_gen": "off",
    "overlay_fps": "1", "overlay_frametime": "1", "overlay_gpu": "0", "overlay_cpu": "0", "overlay_ram": "0",
    "overlay_vram": "0", "overlay_upscaler": "1", "overlay_corner": "1", "overlay_layout": "0",
    "overlay_scale": "100", "overlay_opacity": "50",
}
# Keys of the ini the launcher writes only when they are changed (the start script has the same default).
INI_OPTIONAL_DEFAULTS: dict[str, str] = {"menu_shortcut": "lt_r3"}
# The resolutions offered (the output size at 16:9) and the frame rate limits. Above 120 FPS the games' movement
# timing breaks (Drake's Fortune: Nate fell through the world), so faster or unlimited values read as 120.
RESOLUTIONS: tuple[str, ...] = ("960x540", "1280x720", "1600x900", "1920x1080", "2560x1440", "2880x1620",
                                "3840x2160")
ASPECTS: tuple[str, ...] = ("16:10", "16:9", "21:9", "32:9")
MAX_FPS = 120
FPS_LIMITS: tuple[str, ...] = ("30", "40", "45", "50", "55", "60", "75", "90", "100", str(MAX_FPS))
CHEATS: tuple[str, ...] = ("skipintro", "invincible", "ammo", "noreload", "grenades", "onehit", "treasures",
                           "rewards")
DEFAULT_GAME_DIR = paths.ROOT / "game" / "CUSA02344" / "uroot"


class Config:
    """launcher.json as read, with every missing value at its default."""

    def __init__(self, data: dict[str, Any], file: Path) -> None:
        self.data = data
        self.file = file

    @classmethod
    def load(cls, file: Path | None = None) -> Config:
        file = file or paths.config_file()
        try:
            stored = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = {}
        data = {**LAUNCHER_DEFAULTS, **(stored if isinstance(stored, dict) else {})}
        # An older version let the player choose an update folder for any game folder: a game's update is the one
        # beside its folder now (game_files.update_next_to_game), so the old choice is dropped.
        data.pop("update_dir", None)
        stored_games = data.get("games") if isinstance(data.get("games"), dict) else {}
        data["games"] = {key: _game_entry(stored_games.get(key)) for key in games.KEYS}
        data.setdefault("version", CONFIG_VERSION)
        return cls(data, file)

    def save(self) -> None:
        safe_write.write_text(self.file, json.dumps(self.data, indent=2))

    def game(self, key: str) -> dict[str, Any]:
        return self.data["games"][key]

    @property
    def selected(self) -> str:
        key = str(self.data.get("game"))
        return key if key in games.KEYS else games.KEYS[0]

    @selected.setter
    def selected(self, key: str) -> None:
        self.data["game"] = games.by_key(key).key

    def game_dir(self) -> Path:
        folder = str(self.data.get("game_dir") or "")
        return Path(folder) if folder else DEFAULT_GAME_DIR

    def cheats(self) -> list[str]:
        return [name for name in CHEATS if self.data.get("cheat_" + name)]


def _game_entry(stored: Any) -> dict[str, Any]:
    """A game's settings with its defaults; a value no version offers (a hand edit) falls back alone."""
    entry = {**GAME_DEFAULTS, **(stored if isinstance(stored, dict) else {})}
    if isinstance(entry.get("own_controls"), dict):
        entry["own_controls"] = dict(entry["own_controls"])  # never the defaults' own dict
    if entry["preset"] == "balanced":  # an old preset's name
        entry["preset"] = "medium"
    if entry["resolution"] not in RESOLUTIONS:
        entry["resolution"] = GAME_DEFAULTS["resolution"]
    if entry["aspect"] not in ASPECTS:
        entry["aspect"] = GAME_DEFAULTS["aspect"]
    return entry


def fps_limit(value: str) -> str:
    """A listed frame rate limit; unlimited (0) and faster ones (older versions offered 144-240) are the most."""
    if value in FPS_LIMITS:
        return value
    try:
        number = int(value)
    except ValueError:
        return INI_DEFAULTS["fps_limit"]
    return str(MAX_FPS) if number == 0 or number > MAX_FPS else INI_DEFAULTS["fps_limit"]


def ini_file(key: str) -> Path:
    return paths.USER_DIR / f"probe-{key}.ini"


def read_ini(key: str) -> dict[str, str]:
    values = dict(INI_DEFAULTS)
    for line in _ini_lines(key):
        if "=" in line and not line.lstrip().startswith("#"):
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip()
    values["fps_limit"] = fps_limit(values["fps_limit"])
    return values


def write_ini(key: str, updates: dict[str, str]) -> None:
    """Changes the given keys in place and keeps every other line (the in-game menu writes more keys)."""
    lines = _ini_lines(key)
    done = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            name = line.split("=", 1)[0].strip()
            if name in updates:
                lines[i] = f"{name}={updates[name]}"
                done.add(name)
    lines += [f"{name}={value}" for name, value in updates.items() if name not in done]
    safe_write.write_text(ini_file(key), "\n".join(lines) + "\n")


def _ini_lines(key: str) -> list[str]:
    try:
        return ini_file(key).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ["# Uncharted settings (launcher and in-game menu)"]
