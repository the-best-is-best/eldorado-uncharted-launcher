# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The start script's speed-ups: the update view kept between starts, save backups only when the data changed."""
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import game_update_view  # noqa: E402
import probe_uncharted  # noqa: E402


def game_and_update(root: Path) -> tuple[Path, Path]:
    game, update = root / "Game", root / "Game-patch"
    for folder in (game, update):
        (folder / "sce_sys").mkdir(parents=True)
        (folder / "eboot.bin").write_bytes(b"code " + folder.name.encode())
        (folder / "sce_sys" / "param.sfo").write_bytes(b"sfo")
    (game / "u1data").mkdir()
    (game / "u1data" / "a.psarc").write_bytes(b"game a")
    (update / "u1data").mkdir()
    (update / "u1data" / "b.psarc").write_bytes(b"update b")
    return game, update


def test_the_view_is_kept_until_a_folder_changes(tmp_path) -> None:
    game, update = game_and_update(tmp_path)
    views = tmp_path / "views"
    view = game_update_view.build_view(game, update, views)
    assert game_update_view.LAST_VIEW == "made"
    assert (view / "eboot.bin").read_bytes() == b"code Game-patch"
    assert {p.name for p in (view / "u1data").iterdir()} == {"a.psarc", "b.psarc"}
    game_update_view.build_view(game, update, views)
    assert game_update_view.LAST_VIEW == "kept"
    time.sleep(0.05)
    (update / "u1data" / "c.psarc").write_bytes(b"new in the update")  # a new file: its folder's time changes
    os.utime(update / "u1data")
    view = game_update_view.build_view(game, update, views)
    assert game_update_view.LAST_VIEW == "made" and (view / "u1data" / "c.psarc").is_file()


def test_a_backup_is_made_only_when_the_save_data_changed(tmp_path) -> None:
    save, meta = tmp_path / "SAVEDATA012", tmp_path / "SAVEDATA012.sce_sys"
    save.mkdir()
    meta.mkdir()
    (save / "USR-DATA").write_bytes(b"progress 1")
    (meta / "param.bin").write_bytes(b"param")
    (meta / "thumb.png").write_bytes(b"picture 1")
    first = probe_uncharted.save_signature(save, meta)
    time.sleep(0.05)
    (save / "USR-DATA").write_bytes(b"progress 1")  # rewritten, same data: a new time only
    (meta / "thumb.png").write_bytes(b"picture 2")  # the picture is not the save's data
    (meta / probe_uncharted.SAVE_VERSION_FILE).write_text("1.02")
    assert probe_uncharted.save_signature(save, meta) == first
    (save / "USR-DATA").write_bytes(b"progress 2")
    assert probe_uncharted.save_signature(save, meta) != first
