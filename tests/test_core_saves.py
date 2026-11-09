# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
# Every test builds its own save folders in a temporary folder: no real save is ever touched.
import os
import struct
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import saves  # noqa: E402

TITLE = "CUSA02320"
PROFILES = {"u1": "1", "u2": "1", "u3": "1"}


def param_bytes(subtitle: str, detail: str = "", stamp: int = 1_790_000_000) -> bytes:
    data = bytearray(saves.PARAM_SIZE)
    for (offset, size), text in ((saves.PARAM_TITLE, "Uncharted"), (saves.PARAM_SUBTITLE, subtitle),
                                 (saves.PARAM_DETAIL, detail)):
        encoded = text.encode("utf-8")[:size - 1]
        data[offset:offset + len(encoded)] = encoded
    struct.pack_into("<q", data, saves.PARAM_TIME, stamp)
    return bytes(data)


def make_save(holder: Path, name: str, subtitle: str = "Chapter 1", stamp: int = 1_790_000_000,
              thumb: bool = True, content: str = "data") -> None:
    (holder / name).mkdir(parents=True)
    (holder / name / "USR-DATA").write_text(content)
    meta = holder / f"{name}.sce_sys"
    meta.mkdir()
    (meta / "param.bin").write_bytes(param_bytes(subtitle, "61 treasures\n", stamp))
    (meta / "icon0.png").write_bytes(b"icon")
    if thumb:
        (meta / "thumb.png").write_bytes(b"thumb")


def live_title(user: Path) -> Path:
    return user / "savedata" / "1" / TITLE


def test_lists_game_saves_of_all_games_newest_first(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012", "U1", 100)
    make_save(title, "SAVEDATA021", "U2", 300, thumb=False)
    make_save(title, "SAVEDATA030", "U3", 200)
    make_save(title, "SAVEDATA01P", "profile", 400)
    make_save(title, "SAVEDATA0CC", "shared", 500)
    make_save(title, "SAVEDATA013", "", 600)  # a system save: no chapter line
    found = saves.list_saves(tmp_path, saves.SAVES, PROFILES)
    assert [(s.name, s.game) for s in found] == [("SAVEDATA021", "u2"), ("SAVEDATA030", "u3"), ("SAVEDATA012", "u1")]
    assert found[0].picture == title / "SAVEDATA021.sce_sys" / "icon0.png"
    assert found[1].picture == title / "SAVEDATA030.sce_sys" / "thumb.png"
    assert found[0].detail == "61 treasures"


def test_each_game_reads_its_own_profile(tmp_path: Path) -> None:
    make_save(live_title(tmp_path), "SAVEDATA012")
    make_save(tmp_path / "savedata" / "2" / TITLE, "SAVEDATA021")
    found = saves.list_saves(tmp_path, saves.SAVES, {"u1": "1", "u2": "2", "u3": "1"})
    assert sorted(s.name for s in found) == ["SAVEDATA012", "SAVEDATA021"]
    assert saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0].name == "SAVEDATA012"


def test_arabic_text_shown_as_stored_with_spaces() -> None:
    assert saves.readable("ﺔﻠ_ﻤﺣ") == "ﺔﻠ ﻤﺣ"
    assert saves.readable("Chapter_1") == "Chapter_1"


def test_delete_moves_save_meta_and_last_good_copy(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012")
    saves.last_good_copy(title, "SAVEDATA012").mkdir(parents=True)  # the engine's (<title>.backups/auto)
    (title / ".backup" / "SAVEDATA012").mkdir(parents=True)  # the old place, before engine 0.3.6.49
    save = saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0]
    trash = saves.delete(tmp_path, save)
    assert not (title / "SAVEDATA012").exists() and not (title / "SAVEDATA012.sce_sys").exists()
    assert trash.parent == tmp_path / "savedata-deleted" / "1" / TITLE
    assert (trash / "SAVEDATA012" / "USR-DATA").is_file()
    assert (trash / "SAVEDATA012.sce_sys" / "param.bin").is_file()
    assert (trash / "backup").is_dir() and (trash / "backup-old").is_dir()
    assert not saves.last_good_copy(title, "SAVEDATA012").exists()
    deleted = saves.list_saves(tmp_path, saves.DELETED, PROFILES)
    assert [s.name for s in deleted] == ["SAVEDATA012"]


def test_failed_move_puts_everything_back(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012")
    trash = tmp_path / "trash"
    trash.mkdir()
    (trash / "SAVEDATA012.sce_sys").mkdir()  # in the way of the second rename
    moves = [(title / "SAVEDATA012", trash / "SAVEDATA012"),
             (title / "SAVEDATA012.sce_sys", trash / "SAVEDATA012.sce_sys")]
    with pytest.raises(saves.SaveError):
        saves.move_all(moves)
    assert (title / "SAVEDATA012" / "USR-DATA").is_file()
    assert not (trash / "SAVEDATA012").exists()


def test_restore_brings_deleted_save_back(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012")
    saves.last_good_copy(title, "SAVEDATA012").mkdir(parents=True)
    trash = saves.delete(tmp_path, saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0])
    saves.restore(tmp_path, saves.list_saves(tmp_path, saves.DELETED, PROFILES)[0])
    assert (title / "SAVEDATA012" / "USR-DATA").is_file()
    assert (title / "SAVEDATA012.sce_sys" / "thumb.png").is_file()
    assert saves.last_good_copy(title, "SAVEDATA012").is_dir()
    assert not trash.exists()


def test_restore_refused_when_slot_is_taken(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012", content="old")
    saves.delete(tmp_path, saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0])
    make_save(title, "SAVEDATA012", content="new")
    with pytest.raises(saves.SaveError):
        saves.restore(tmp_path, saves.list_saves(tmp_path, saves.DELETED, PROFILES)[0])
    assert (title / "SAVEDATA012" / "USR-DATA").read_text() == "new"
    assert len(saves.list_saves(tmp_path, saves.DELETED, PROFILES)) == 1


def test_delete_for_good_removes_it_and_older_backups(tmp_path: Path) -> None:
    deleted = tmp_path / "savedata-deleted" / "1" / TITLE / "SAVEDATA012-20261105-120000"
    make_save(deleted, "SAVEDATA012")
    backups = tmp_path / "savedata-backups" / "1" / TITLE
    make_save(backups / "SAVEDATA012-20261105-110000", "SAVEDATA012")
    make_save(backups / "SAVEDATA012-20261105-130000", "SAVEDATA012")
    make_save(backups / "SAVEDATA021-20261105-110000", "SAVEDATA021")
    saves.delete_for_good(tmp_path, saves.list_saves(tmp_path, saves.DELETED, PROFILES)[0])
    assert not deleted.exists()
    assert not (backups / "SAVEDATA012-20261105-110000").exists()
    assert (backups / "SAVEDATA012-20261105-130000").is_dir()
    assert (backups / "SAVEDATA021-20261105-110000").is_dir()


def test_delete_for_good_refuses_live_saves(tmp_path: Path) -> None:
    make_save(live_title(tmp_path), "SAVEDATA012")
    with pytest.raises(saves.SaveError):
        saves.delete_for_good(tmp_path, saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0])
    assert (live_title(tmp_path) / "SAVEDATA012").is_dir()


def test_backups_only_of_saves_that_exist_newest_first(tmp_path: Path) -> None:
    make_save(live_title(tmp_path), "SAVEDATA012")
    backups = tmp_path / "savedata-backups" / "1" / TITLE
    make_save(backups / "SAVEDATA012-20261105-110000", "SAVEDATA012")
    make_save(backups / "SAVEDATA012-20261105-130000", "SAVEDATA012")
    make_save(backups / "SAVEDATA021-20261105-140000", "SAVEDATA021")  # its save is gone
    found = saves.list_saves(tmp_path, saves.BACKUPS, PROFILES)
    assert [s.holder.name for s in found] == ["SAVEDATA012-20261105-130000", "SAVEDATA012-20261105-110000"]


def test_restore_backup_sends_current_save_to_deleted(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012", content="current")
    copy = tmp_path / "savedata-backups" / "1" / TITLE / "SAVEDATA012-20261105-110000"
    make_save(copy, "SAVEDATA012", content="backup")
    (copy / "signature.txt").write_text("sig")
    replaced = saves.restore_backup(tmp_path, saves.list_saves(tmp_path, saves.BACKUPS, PROFILES)[0])
    assert (title / "SAVEDATA012" / "USR-DATA").read_text() == "backup"
    assert replaced is not None and (replaced / "SAVEDATA012" / "USR-DATA").read_text() == "current"
    assert (copy / "SAVEDATA012" / "USR-DATA").read_text() == "backup"  # the backup stays
    assert not any(p.name.startswith(".restore") for p in title.iterdir())


def test_unknown_view_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        saves.list_saves(tmp_path, "trash", PROFILES)


def test_latest_and_recent_follow_the_list_order(tmp_path: Path) -> None:
    title = live_title(tmp_path)
    make_save(title, "SAVEDATA012", "U1 old", 100)
    make_save(title, "SAVEDATA013", "U1 new", 300)
    make_save(title, "SAVEDATA021", "U2", 200)
    found = saves.list_saves(tmp_path, saves.SAVES, PROFILES)
    latest = saves.latest(found, "u1")
    assert latest is not None and latest.chapter == "U1 new"
    assert saves.latest(found, "u3") is None
    assert [s.chapter for s in saves.recent(found, 2)] == ["U1 new", "U2"]
    assert saves.recent([], 5) == []


def test_saved_at_falls_back_to_the_folder_time(tmp_path: Path) -> None:
    make_save(live_title(tmp_path), "SAVEDATA012", stamp=1_790_000_000)
    save = saves.list_saves(tmp_path, saves.SAVES, PROFILES)[0]
    assert saves.saved_at(save) == 1_790_000_000
    unstamped = replace(save, time=0.0)
    os.utime(unstamped.data, (1_700_000_000, 1_700_000_000))
    assert saves.saved_at(unstamped) == 1_700_000_000
    assert saves.saved_at(replace(unstamped, holder=tmp_path / "gone")) == 0.0


def test_when_text_reads_as_spoken() -> None:
    now = time.mktime((2026, 11, 7, 15, 0, 0, 0, 0, -1))
    assert saves.when_text(now - 3600, now) == "today 14:00"
    assert saves.when_text(now - 86400, now) == "yesterday 15:00"
    assert saves.when_text(now - 3 * 86400, now) == "3 days ago"
    assert saves.when_text(now - 40 * 86400, now) == "28 Sep 2026"
    assert saves.when_text(0, now) == ""


def test_a_save_of_a_newer_game_version_is_left_out(tmp_path) -> None:
    from core import saves as saves_module

    def save(version: str) -> saves_module.Save:
        meta = tmp_path / f"m{version or 'none'}"
        meta.mkdir()
        if version:
            (meta / saves_module.VERSION_FILE).write_text(version, encoding="utf-8")
        return saves_module.Save("saves", "u1", "SAVEDATA012", "1", "CUSA02320", tmp_path, "c", "d", 0.0, None,
                                 saves_module.version_of(meta))

    newer, same, older, unknown = save("01.03"), save("01.02"), save("01.00"), save("")
    shown = saves_module.playable([newer, same, older, unknown], "01.02")
    assert newer not in shown and same in shown and older in shown and unknown in shown
    assert saves_module.playable([newer], "") == [newer]   # the chosen copy's version unknown: nothing hidden
