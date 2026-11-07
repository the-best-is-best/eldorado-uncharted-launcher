# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
# Every test builds its own game folder in a temporary folder; no picture is read (art.py only decides).
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import art, games  # noqa: E402

U1, U2 = games.by_key("u1"), games.by_key("u2")


def sfo_bytes(values: dict[str, str]) -> bytes:
    """A param.sfo with text values only (the layout game_files.sfo_values reads)."""
    keys = b"".join(key.encode() + b"\0" for key in values)
    entries, data, key_at, value_at = b"", b"", 0, 0
    for key, value in values.items():
        raw = value.encode() + b"\0"
        entries += struct.pack("<HHIII", key_at, 0x0204, len(raw), len(raw), value_at)
        data += raw
        key_at += len(key) + 1
        value_at += len(raw)
    keys_at = 20 + 16 * len(values)
    header = struct.pack("<IIIII", 0x46535000, 0x0101, keys_at, keys_at + len(keys), len(values))
    return header + entries + keys + data


def game_dir(tmp_path: Path, title: str, pictures: tuple[str, ...] = ("pic0.png", "pic1.png")) -> Path:
    folder = tmp_path / "game"
    (folder / "sce_sys").mkdir(parents=True)
    (folder / "sce_sys" / "param.sfo").write_bytes(sfo_bytes({"TITLE": title, "APP_VER": "01.02"}))
    for name in pictures:
        (folder / "sce_sys" / name).write_bytes(b"png")
    return folder


def test_edition_from_the_title(tmp_path: Path) -> None:
    assert art.is_arabic_edition(game_dir(tmp_path, "أنشارتد: مجموعة نيثان دريك"))
    assert not art.is_arabic_edition(game_dir(tmp_path / "b", "Uncharted: The Nathan Drake Collection"))
    assert not art.is_arabic_edition(tmp_path / "missing")


def test_art_file_order(tmp_path: Path) -> None:
    folder = game_dir(tmp_path, "x")
    assert art.art_file(folder, arabic=True) == folder / "sce_sys" / "pic0.png"
    assert art.art_file(folder, arabic=False) == folder / "sce_sys" / "pic1.png"
    (folder / "sce_sys" / "pic1.png").unlink()
    assert art.art_file(folder, arabic=False) == folder / "sce_sys" / "pic0.png"
    assert art.art_file(tmp_path / "nothing", arabic=False) is None


def test_save_picture_comes_first(tmp_path: Path) -> None:
    folder = game_dir(tmp_path, "Uncharted")
    thumb = tmp_path / "thumb.png"
    thumb.write_bytes(b"png")
    picture = art.choose(thumb, folder, U1)
    assert picture.kind == art.SAVE and picture.path == thumb and picture.fills
    assert picture.region == art.WHOLE
    # A picture that is gone falls back to the game's art.
    assert art.choose(tmp_path / "gone.png", folder, U1).kind == art.ART


def test_original_edition_shows_its_key_art_whole(tmp_path: Path) -> None:
    folder = game_dir(tmp_path, "Uncharted: The Nathan Drake Collection")
    picture = art.choose(None, folder, U2)
    assert picture.kind == art.ART and picture.path == folder / "sce_sys" / "pic1.png"
    assert picture.region == art.WHOLE and picture.fills


def test_arabic_edition_shows_the_games_third_below_the_mark(tmp_path: Path) -> None:
    folder = game_dir(tmp_path, "أنشارتد")
    picture = art.choose(None, folder, U2)
    assert picture.kind == art.COVER and picture.path == folder / "sce_sys" / "pic0.png"
    assert picture.region == art.Region(1 / 3, art.COVER_TOP_CUT, 2 / 3, 1.0)
    assert not picture.fills


def test_nothing_to_show_is_drawn(tmp_path: Path) -> None:
    folder = game_dir(tmp_path, "Uncharted", pictures=())
    assert art.choose(None, folder, U1) == art.NOTHING
    assert art.choose(None, tmp_path / "missing", U1).kind == art.DRAWN


def test_version_follows_the_file(tmp_path: Path) -> None:
    picture = tmp_path / "thumb.png"
    picture.write_bytes(b"png")
    first = art.version_of(picture)
    os.utime(picture, (1_800_000_000, 1_800_000_000))
    assert art.version_of(picture) != first
    assert art.version_of(picture) == art.version_of(picture)
    assert art.version_of(tmp_path / "other.png") != art.version_of(picture)


def test_fill_keeps_the_aspect_and_centers() -> None:
    assert art.fill_rect(1920, 1080, art.WHOLE, 1080, 720) == art.Rect(150, 0, 1620, 1080)
    assert art.fill_rect(960, 540, art.WHOLE, 1080, 720) == art.Rect(75, 0, 810, 540)
    # A tall region in a wide target: cut top and bottom, inside the region.
    tall = art.Region(0, art.COVER_TOP_CUT, 1 / 3, 1.0)
    assert art.fill_rect(1920, 1080, tall, 1080, 720) == art.Rect(0, 418, 640, 427)
    assert art.fill_rect(0, 0, art.WHOLE, 1080, 720) == art.Rect(0, 0, 1, 1)


def test_cover_stands_on_the_right_as_tall_as_the_screen() -> None:
    third = art.Region(0, art.COVER_TOP_CUT, 1 / 3, 1.0)
    source, place = art.cover_rects(1920, 1080, third, 1080, 720)
    assert source == art.Rect(0, 184, 640, 896)
    assert place == art.Rect(566, 0, 514, 720)
    # A wide screen: at least 42% of the width, cut evenly at the top and the bottom.
    source, place = art.cover_rects(1920, 1080, third, 2000, 600)
    assert place == art.Rect(1160, 0, 840, 600)
    assert source.height == 457 and source.y == 403


def test_enlargement_says_when_to_soften() -> None:
    assert art.enlargement(art.Rect(0, 0, 228, 128), 1080) > art.SOFTEN_ABOVE
    assert art.enlargement(art.Rect(0, 0, 960, 540), 1080) < art.SOFTEN_ABOVE
    assert art.enlargement(art.Rect(0, 0, 0, 0), 1080) == 1.0
