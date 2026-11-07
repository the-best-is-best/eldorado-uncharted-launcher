# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The picture behind the selected game on the home screen: the latest save's picture (where the player left
off), else the player's own art from the game folder (sce_sys), else El Dorado's drawn map. This module only
decides: which file, which part of it, how it sits on the screen. ui/background.py draws the choice. No Qt here."""
from __future__ import annotations

import zlib
from dataclasses import dataclass
from pathlib import Path

from . import game_files, games

SAVE, COVER, ART, DRAWN = "save", "cover", "art", "drawn"
# The Arabic edition names itself in Arabic in sce_sys/param.sfo, and its art (pic0.png) is the three games'
# covers side by side with a repack's mark in the top strip: a game shows its third, below that strip. The
# original's art is one picture of Drake (pic1.png, as the released launcher shows it).
ARABIC_LETTERS = ("؀", "ۿ")
COVER_TOP_CUT = 0.17
# A cover stands on the right as tall as the screen, and takes at least this much of its width (on a wide screen
# it is cut evenly at the top and the bottom instead).
COVER_LEAST_WIDTH = 0.42
# A save picture enlarged past this (icon0.png, 228x128, from before the engine wrote thumb.png) is softened.
SOFTEN_ABOVE = 1.6


@dataclass(frozen=True)
class Region:
    """A part of a picture, as fractions of its width and height (0..1)."""
    left: float = 0.0
    top: float = 0.0
    right: float = 1.0
    bottom: float = 1.0


@dataclass(frozen=True)
class Rect:
    """Pixels of a picture or of the screen."""
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Picture:
    kind: str                  # save, cover, art or drawn
    path: Path | None = None   # drawn: none
    region: Region = Region()  # the part of the file to show
    version: str = "0"         # changes with the file (its time and name); the image URL carries it

    @property
    def fills(self) -> bool:
        """Scaled and cut to fill the screen (a save picture, the original's art); a cover stands on the right."""
        return self.kind != COVER


WHOLE = Region()
NOTHING = Picture(DRAWN)


# --- the choice ------------------------------------------------------------------------------------------------


def has_arabic(text: str) -> bool:
    low, high = ARABIC_LETTERS
    return any(low <= char <= high for char in text)


def is_arabic_edition(game_dir: Path) -> bool:
    return has_arabic(game_files.sfo_values(game_dir).get("TITLE", ""))


def art_file(game_dir: Path, arabic: bool) -> Path | None:
    """The player's own art in the game folder: the three covers (pic0) for the Arabic edition, the key art (pic1)
    for the original; the other file when that one is missing."""
    names = ("pic0.png", "pic1.png") if arabic else ("pic1.png", "pic0.png")
    for name in names:
        path = game_dir / "sce_sys" / name
        if path.is_file():
            return path
    return None


def version_of(path: Path) -> str:
    """A token that changes when the file changes (its time) or another file is chosen (its name): the image URL
    carries it, so the picture is read again only then."""
    try:
        stamp = int(path.stat().st_mtime)
    except OSError:
        stamp = 0
    return f"{stamp}-{zlib.crc32(str(path).encode('utf-8')):08x}"


def game_art(game_dir: Path, game: games.Game) -> Picture | None:
    arabic = is_arabic_edition(game_dir)
    path = art_file(game_dir, arabic)
    if path is None:
        return None
    if not arabic:
        return Picture(ART, path, WHOLE, version_of(path))
    index = int(game.number) - 1
    return Picture(COVER, path, Region(index / 3, COVER_TOP_CUT, (index + 1) / 3, 1.0), version_of(path))


def choose(latest_save_picture: Path | None, game_dir: Path, game: games.Game) -> Picture:
    """The home screen's picture for a game: its latest save's picture, else its own art, else the drawn map."""
    if latest_save_picture is not None and latest_save_picture.is_file():
        return Picture(SAVE, latest_save_picture, WHOLE, version_of(latest_save_picture))
    return game_art(game_dir, game) or NOTHING


# --- the cut (pure geometry, so it is tested without a picture) ---------------------------------------------------


def _region_pixels(width: int, height: int, region: Region) -> tuple[float, float, float, float]:
    return (width * region.left, height * region.top, width * (region.right - region.left),
            height * (region.bottom - region.top))


def fill_rect(width: int, height: int, region: Region, target_width: int, target_height: int) -> Rect:
    """The part of the picture that fills the target without stretching: the region's largest part at the target's
    aspect, centered in the region."""
    x, y, w, h = _region_pixels(width, height, region)
    if w <= 0 or h <= 0 or target_width <= 0 or target_height <= 0:
        return Rect(0, 0, max(1, width), max(1, height))
    if w * target_height > h * target_width:  # wider than the target: the sides go
        shown_w, shown_h = h * target_width / target_height, h
    else:
        shown_w, shown_h = w, w * target_height / target_width
    return Rect(round(x + (w - shown_w) / 2), round(y + (h - shown_h) / 2), max(1, round(shown_w)),
                max(1, round(shown_h)))


def cover_rects(width: int, height: int, region: Region, target_width: int, target_height: int,
                least: float = COVER_LEAST_WIDTH) -> tuple[Rect, Rect]:
    """A cover on the right of the target: as tall as the target and at least `least` of its width (a wide target
    cuts it evenly at the top and the bottom). Returns the part of the picture shown and where it goes."""
    x, y, w, h = _region_pixels(width, height, region)
    if w <= 0 or h <= 0 or target_width <= 0 or target_height <= 0:
        return Rect(0, 0, max(1, width), max(1, height)), Rect(0, 0, max(1, target_width), max(1, target_height))
    scale = max(target_height / h, target_width * least / w)
    shown_h = min(h, target_height / scale)
    source = Rect(round(x), round(y + (h - shown_h) / 2), max(1, round(w)), max(1, round(shown_h)))
    shown_w = max(1, round(w * scale))
    return source, Rect(target_width - shown_w, 0, shown_w, target_height)


def enlargement(source: Rect, target_width: int) -> float:
    """How much the shown part is scaled up (past SOFTEN_ABOVE it is softened rather than shown blocky)."""
    return target_width / source.width if source.width else 1.0
