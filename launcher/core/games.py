# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The three games of the Collection: one table every other module reads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Game:
    key: str          # u1, u2, u3: settings, ini files and environment names use it
    number: str       # the roman-free number shown on the card
    title: str        # the card's title
    name: str         # the full name
    executable: str   # the file tools/probe_uncharted.py starts (--executable)
    place: str        # where the story goes (decoration under the title)


GAMES: tuple[Game, ...] = (
    Game("u1", "1", "DRAKE'S FORTUNE", "Uncharted: Drake's Fortune", "eboot.bin", "PANAMA COAST"),
    Game("u2", "2", "AMONG THIEVES", "Uncharted 2: Among Thieves", "big2-ps4_Shipping.elf", "HIMALAYAS"),
    Game("u3", "3", "DRAKE'S DECEPTION", "Uncharted 3: Drake's Deception", "big3-ps4_Shipping.elf",
         "RUB' AL KHALI"),
)
KEYS: tuple[str, ...] = tuple(game.key for game in GAMES)


def by_key(key: str) -> Game:
    for game in GAMES:
        if game.key == key:
            return game
    raise KeyError(f"no game {key!r}")


def is_game_dir(folder: Path | str | None) -> bool:
    """The Collection's game folder: eboot.bin and sce_sys/param.sfo."""
    if not folder:
        return False
    path = Path(folder)
    return (path / "eboot.bin").is_file() and (path / "sce_sys" / "param.sfo").is_file()
