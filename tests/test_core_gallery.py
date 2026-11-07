# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import gallery  # noqa: E402


def _shot(folder: Path, name: str, when: int) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(b"png")
    os.utime(path, (when, when))
    return path


def test_shots_newest_first_pictures_only(tmp_path: Path) -> None:
    folder = gallery.folder("u1", tmp_path)
    _shot(folder, "20261101-100000.png", 1000)
    _shot(folder, "20261102-100000.PNG", 3000)
    _shot(folder, "notes.txt", 5000)
    (folder / "sub.png").mkdir()
    names = [shot.name for shot in gallery.shots("u1", tmp_path)]
    assert names == ["20261102-100000.PNG", "20261101-100000.png"]


def test_label_from_the_file_name(tmp_path: Path) -> None:
    assert gallery.Shot(tmp_path / "20261105-234255.png", 0.0).label() == "05 Nov 2026  23:42"


def test_no_folder_no_shots(tmp_path: Path) -> None:
    assert gallery.shots("u3", tmp_path) == []


def test_delete_refuses_a_file_that_is_gone(tmp_path: Path) -> None:
    shot = gallery.Shot(tmp_path / "gone.png", 0.0)
    try:
        gallery.delete(shot)
    except gallery.GalleryError:
        return
    raise AssertionError("no error for a missing screenshot")


def test_delete_goes_through_the_recycle_bin(tmp_path: Path) -> None:
    path = _shot(tmp_path, "a.png", 1)
    taken: list[Path] = []
    original = gallery.recycle
    gallery.recycle = taken.append  # the real one would fill the player's Recycle Bin
    try:
        gallery.delete(gallery.Shot(path, 1.0))
    finally:
        gallery.recycle = original
    assert taken == [path]


if __name__ == "__main__":
    import tempfile

    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            with tempfile.TemporaryDirectory() as folder:
                test(Path(folder))
            print("ok", name)
