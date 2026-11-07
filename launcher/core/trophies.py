# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Each game's trophy set and how much of it the player has earned.

The engine's engine/scripts/trophies.py reads the player's own trophy pack (Game/sce_sys/trophy/trophy0N.trp)
into USER/cache/hub-trophy/<key> (trophies.txt plus the pack's TROPnnn.PNG icons); the game writes each unlock to
USER/trophy/<NP id>.log. This module only reads those: no trophy text or picture ships with the launcher."""
from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from . import paths, safe_write
from .i18n import t

GRADES: tuple[str, ...] = ("P", "G", "S", "B")
GRADE_NAMES: dict[str, str] = {"P": "PLATINUM", "G": "GOLD", "S": "SILVER", "B": "BRONZE"}
# The old engine's unlock files and the set each belongs to (merged into <NP id>.log once).
OLD_LOGS: dict[str, str] = {"trophy01.txt": "NPWR09798_00", "trophy02.txt": "NPWR09799_00",
                            "trophy03.txt": "NPWR09801_00"}
ENGINE_SCRIPT = paths.ROOT / "engine" / "scripts" / "trophies.py"


class TrophyError(Exception):
    """The trophy reader could not be loaded or a set could not be read."""


@dataclass(frozen=True)
class Trophy:
    number: int
    grade: str        # P, G, S or B
    hidden: bool
    name: str
    detail: str
    earned: int       # unlock time (seconds since 1970); 0 = locked
    icon: Path | None

    @property
    def secret(self) -> bool:
        """A hidden trophy not earned yet: its name and text stay hidden, as on the console."""
        return self.hidden and not self.earned

    def shown_name(self) -> str:
        return t("Hidden trophy") if self.secret else self.name

    def shown_detail(self) -> str:
        return t("Keep playing to find it.") if self.secret else self.detail

    def earned_text(self) -> str:
        if not self.earned:
            return t("LOCKED")
        # Some logs carry 1 as the time (unlocked by a tool): earned, date unknown.
        return time.strftime("%d %b %Y", time.localtime(self.earned)) if self.earned > 1 else t("EARNED")


@dataclass(frozen=True)
class GradeCount:
    grade: str
    earned: int
    total: int

    @property
    def name(self) -> str:
        return GRADE_NAMES[self.grade]


@dataclass(frozen=True)
class TrophySet:
    key: str
    npcommid: str
    title: str
    trophies: tuple[Trophy, ...]   # earned first (newest first), then the rest in the game's order

    @property
    def count(self) -> int:
        return sum(1 for trophy in self.trophies if trophy.earned)

    @property
    def percent(self) -> int:
        return self.count * 100 // len(self.trophies) if self.trophies else 0

    def grades(self) -> list[GradeCount]:
        """The count of each grade the set has (a set without platinum shows no platinum line)."""
        result = []
        for grade in GRADES:
            of_grade = [trophy for trophy in self.trophies if _grade(trophy.grade) == grade]
            if of_grade:
                result.append(GradeCount(grade, sum(1 for t in of_grade if t.earned), len(of_grade)))
        return result


def _grade(grade: str) -> str:
    return grade if grade in GRADES else "B"


def load_engine(script: Path | None = None) -> ModuleType:
    """The engine's trophy reader, loaded from its file (it is a script, not a package)."""
    script = script or ENGINE_SCRIPT
    spec = importlib.util.spec_from_file_location("eldorado_engine_trophies", script)
    if spec is None or spec.loader is None:
        raise TrophyError(f"the trophy reader is missing ({script})")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (OSError, SyntaxError, ImportError) as error:
        raise TrophyError(f"the trophy reader could not be loaded ({error})") from error
    return module


def cache_dir(key: str, user_dir: Path | None = None) -> Path:
    return (user_dir or paths.USER_DIR) / "cache" / "hub-trophy" / key


def language_number(value: object) -> int:
    """The pack's text language (TROP_<n>.ESFM) for a launcher language setting; "ar" and others -> 1 (English),
    as the packs carry no Arabic texts."""
    text = str(value)
    return int(text) if text.isdigit() else 1


def migrate_old_logs(user_dir: Path | None = None) -> int:
    """Merges the old engine's trophy0N.txt unlocks into <NP id>.log (lines already there are kept), then renames
    the old file to *.migrated so it happens once. Returns the number of unlocks moved."""
    folder = (user_dir or paths.USER_DIR) / "trophy"
    moved = 0
    for old_name, npcommid in OLD_LOGS.items():
        old = folder / old_name
        if not old.is_file():
            continue
        new = folder / f"{npcommid}.log"
        have = new.read_text(encoding="utf-8", errors="replace") if new.is_file() else ""
        known = {_unlock_id(line) for line in have.splitlines()} - {None}
        extra = []
        for line in old.read_text(encoding="utf-8", errors="replace").splitlines():
            number = _unlock_id(line)
            if number is not None and number not in known:
                extra.append(line.strip())
                known.add(number)
        if extra:
            body = have if not have or have.endswith("\n") else have + "\n"
            safe_write.write_text(new, body + "\n".join(extra) + "\n")
        old.rename(old.with_name(old_name + ".migrated"))
        moved += len(extra)
    return moved


def _unlock_id(line: str) -> str | None:
    """The trophy number of an unlock line ("<number> <time>"), or None for a broken line."""
    part = line.split()
    return part[0] if len(part) >= 2 and part[0].isdigit() and part[1].isdigit() else None


def load(key: str, game_dir: Path, language: int = 1, user_dir: Path | None = None,
         engine: ModuleType | None = None) -> TrophySet | None:
    """The game's set with the player's unlocks, or None when no trophy pack was ever read for it.

    The cache is made again from the pack when the pack or the language changed. Without the pack (the game folder
    moved) the cache made earlier is still shown: the engine's prepare() would remove it."""
    user_dir = user_dir or paths.USER_DIR
    engine = engine or load_engine()
    folder = cache_dir(key, user_dir)
    try:
        if engine.trp_for(game_dir, key) is not None:
            engine.prepare(game_dir, key, folder, language)
        info = engine.read_cache(folder)
    except (OSError, ValueError, KeyError) as error:
        raise TrophyError(f"the trophy list of {key} could not be read ({error})") from error
    if not info:
        return None
    unlocked: dict[int, int] = engine.read_unlocks(user_dir, info["npcommid"])
    trophies = [Trophy(number, grade, hidden, name, detail, unlocked.get(number, 0), _icon(folder, number))
                for number, grade, hidden, name, detail in info["trophies"]]
    return TrophySet(key, info["npcommid"], info["title"], _ordered(trophies))


def _icon(folder: Path, number: int) -> Path | None:
    path = folder / f"TROP{number:03d}.PNG"
    return path if path.is_file() else None


def _ordered(trophies: list[Trophy]) -> tuple[Trophy, ...]:
    earned = sorted((t for t in trophies if t.earned), key=lambda t: -t.earned)
    return tuple(earned + [t for t in trophies if not t.earned])
