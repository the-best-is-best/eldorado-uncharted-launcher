# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The player's game saves: the list, delete (to savedata-deleted, as the in-game list does), the deleted saves
(restore, delete for good) and the backups tools/probe_uncharted.py makes before each start (restore).

Layouts under analysis/uncharted-user:
  savedata/<profile>/<title>/<dir> and <dir>.sce_sys (param.bin, thumb.png, icon0.png); <title>/.backup/<dir> is
      the engine's last good copy
  savedata-deleted/<profile>/<title>/<dir>-<YYYYmmdd-HHMMSS>/<dir>, <dir>.sce_sys and backup (the last good copy)
  savedata-backups/<profile>/<title>/<dir>-<YYYYmmdd-HHMMSS>/<dir>, <dir>.sce_sys and signature.txt

Every move is a rename (all on one drive): a save is never half copied, and a failed step puts back the steps done
before it. Only delete_for_good removes files.
"""
from __future__ import annotations

import re
import shutil
import struct
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import games
from .i18n import t

SAVES, DELETED, BACKUPS = "saves", "deleted", "backups"
VIEWS: tuple[str, ...] = (SAVES, DELETED, BACKUPS)
ROOTS: dict[str, str] = {SAVES: "savedata", DELETED: "savedata-deleted", BACKUPS: "savedata-backups"}

# Game saves are SAVEDATA0<game><slot>; SAVEDATA0<game>P and SAVEDATA0CC are the profile and shared saves.
GAME_SAVE = re.compile(r"SAVEDATA0([123])[0-9]$")
STAMP = re.compile(r"-(\d{8}-\d{6})$")
STAMP_FORMAT = "%Y%m%d-%H%M%S"

# param.bin, the save's texts as the game wrote them: title, subtitle (the chapter line), detail, then the time.
PARAM_SIZE = 1328
PARAM_TITLE = (0, 128)
PARAM_SUBTITLE = (128, 128)
PARAM_DETAIL = (256, 1024)
PARAM_TIME = 1288
# Arabic arrives as presentation forms, already in display order; the game writes '_' for some of its spaces.
PRESENTATION_FORMS = (("ﭐ", "﷿"), ("ﹰ", "﻿"))


class SaveError(Exception):
    """A save could not be moved, restored or removed; the message says why, for the player."""


@dataclass(frozen=True)
class Param:
    title: str
    subtitle: str
    detail: str
    time: float


@dataclass(frozen=True)
class Save:
    view: str              # saves, deleted or backups
    game: str              # u1, u2, u3
    name: str              # SAVEDATA012
    profile: str           # the user folder (savedata/<profile>)
    title_id: str          # the game's title folder (CUSA02320)
    holder: Path           # deleted/backups: the <dir>-<stamp> folder; saves: the title folder
    chapter: str           # the line the in-game list shows first
    detail: str
    time: float            # saves/deleted: when the game wrote it; backups: when the copy was made
    picture: Path | None
    version: str = ""      # the game version that wrote it ("01.03"), "" when it was not recorded

    @property
    def data(self) -> Path:
        return self.holder / self.name

    @property
    def meta(self) -> Path:
        return self.holder / f"{self.name}.sce_sys"


# --- reading ---------------------------------------------------------------------------------------------------


def is_presentation_text(text: str) -> bool:
    return any(low <= char <= high for char in text for low, high in PRESENTATION_FORMS)


def readable(text: str) -> str:
    if is_presentation_text(text):
        text = text.replace("_", " ")
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def read_param(meta: Path) -> Param | None:
    try:
        data = (meta / "param.bin").read_bytes()
    except OSError:
        return None
    if len(data) < PARAM_SIZE:
        return None

    def field(place: tuple[int, int]) -> str:
        offset, size = place
        return data[offset:offset + size].split(b"\0")[0].decode("utf-8", "replace")

    stamp = struct.unpack_from("<q", data, PARAM_TIME)[0]
    return Param(field(PARAM_TITLE), field(PARAM_SUBTITLE), field(PARAM_DETAIL), float(stamp))


def picture_of(meta: Path) -> Path | None:
    """The engine's picture of the moment the save was made, else the game's own icon."""
    for name in ("thumb.png", "icon0.png"):
        if (meta / name).is_file():
            return meta / name
    return None


def stamp_time(folder_name: str) -> float:
    """When a deleted save was deleted or a backup was made: the <dir>-<YYYYmmdd-HHMMSS> folder name."""
    match = STAMP.search(folder_name)
    if not match:
        return 0.0
    try:
        return time.mktime(time.strptime(match.group(1), STAMP_FORMAT))
    except ValueError:
        return 0.0


def game_of(name: str) -> str | None:
    match = GAME_SAVE.match(name)
    if not match:
        return None
    for game in games.GAMES:
        if game.number == match.group(1):
            return game.key
    return None


def _entries(title_dir: Path, view: str) -> list[tuple[Path, str]]:
    """(holder, save name) of every folder in a title folder that may be a game save."""
    found = []
    for entry in sorted(title_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if view == SAVES:
            if not entry.name.endswith(".sce_sys"):
                found.append((title_dir, entry.name))
            continue
        name = STAMP.sub("", entry.name)
        if (entry / name).is_dir():
            found.append((entry, name))
    return found


def _make_save(view: str, profile: str, title_dir: Path, holder: Path, name: str) -> Save | None:
    game = game_of(name)
    if game is None:
        return None
    meta = holder / f"{name}.sce_sys"
    param = read_param(meta)
    if param is None or not param.subtitle.strip():
        return None  # not a story save (the game leaves the chapter line empty only on its system saves)
    made = stamp_time(holder.name) if view == BACKUPS else 0.0
    return Save(view, game, name, profile, title_dir.name, holder, readable(param.subtitle),
                readable(param.detail), made or param.time, picture_of(meta), version_of(meta))


# Written by tools/probe_uncharted.py after each run: the game version that wrote the save.
VERSION_FILE = "eldorado-game-version.txt"


def version_of(meta: Path) -> str:
    try:
        return (meta / VERSION_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _version_key(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return ()


def too_new(save: Save, game_version: str) -> bool:
    """A save written by a newer version of the game than the one chosen: the game does not load it, so the
    launcher neither shows nor changes it. A save without a recorded version is shown."""
    made, now = _version_key(save.version), _version_key(game_version)
    return bool(made and now) and made > now


def playable(found: list[Save], game_version: str) -> list[Save]:
    return [save for save in found if not too_new(save, game_version)]


def list_saves(user_dir: Path, view: str, profiles: dict[str, str]) -> list[Save]:
    """The saves of all three games in one view, newest first. profiles: each game's save profile (u1 -> "1").
    Backups are listed only for saves that are there now (a deleted save's copies come back with it)."""
    if view not in VIEWS:
        raise ValueError(f"no save view {view!r}")
    found: list[Save] = []
    for profile in sorted(set(profiles.values())):
        base = user_dir / ROOTS[view] / profile
        if not base.is_dir():
            continue
        for title_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")):
            for holder, name in _entries(title_dir, view):
                save = _make_save(view, profile, title_dir, holder, name)
                if save is not None and profiles.get(save.game) == profile:
                    found.append(save)
    if view == BACKUPS:
        found = [save for save in found if live_place(user_dir, save).is_dir()]
    found.sort(key=lambda save: save.time, reverse=True)
    return found


def live_place(user_dir: Path, save: Save) -> Path:
    """Where the save lives in savedata (its folder, whether it is there or not)."""
    return user_dir / ROOTS[SAVES] / save.profile / save.title_id / save.name


# --- moving ----------------------------------------------------------------------------------------------------


def move_all(moves: list[tuple[Path, Path]]) -> None:
    """Renames each (source, target) in turn. A failed rename puts the done ones back and raises SaveError; a
    rename that cannot be put back is named in the message, so the player knows where the file is."""
    done: list[tuple[Path, Path]] = []
    try:
        for source, target in moves:
            if target.exists():
                raise OSError(f"{target} exists")
            source.rename(target)
            done.append((source, target))
    except OSError as error:
        stuck = _undo(done)
        note = f" Not put back: {', '.join(stuck)}." if stuck else ""
        raise SaveError(f"The save could not be moved: {error}.{note}") from error


def _undo(done: list[tuple[Path, Path]]) -> list[str]:
    stuck = []
    for source, target in reversed(done):
        try:
            target.rename(source)
        except OSError:
            stuck.append(str(target))
    return stuck


def _now_stamp() -> str:
    return time.strftime(STAMP_FORMAT)


def last_good_copy(title_dir: Path, name: str) -> Path:
    """The engine's last good copy of a save (runtime_savedata.c save_backup: <title>.backups/auto/<dir>; it was
    <title>/.backup/<dir> before engine 0.3.6.49)."""
    return title_dir.parent / f"{title_dir.name}.backups" / "auto" / name


def _trash_moves(title_dir: Path, name: str, trash: Path) -> list[tuple[Path, Path]]:
    """The renames that take a live save (folder, its .sce_sys, the engine's last good copy) into trash: the
    parts that are there. A copy left behind would later "repair" a new save of that name with this one's data."""
    parts = [(title_dir / name, trash / name), (title_dir / f"{name}.sce_sys", trash / f"{name}.sce_sys"),
             (last_good_copy(title_dir, name), trash / "backup"), (title_dir / ".backup" / name, trash / "backup-old")]
    return [(source, target) for source, target in parts if source.is_dir()]


def _new_trash(user_dir: Path, profile: str, title_id: str, name: str) -> Path:
    trash = user_dir / ROOTS[DELETED] / profile / title_id / f"{name}-{_now_stamp()}"
    try:
        trash.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        raise SaveError(f"The deleted saves folder could not be made: {error}") from error
    return trash


def _remove_empty(folder: Path) -> None:
    """Removes a folder only when nothing is left in it (a step that left files there keeps them)."""
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()


def delete(user_dir: Path, save: Save) -> Path:
    """Moves a live save to the deleted saves. Returns the folder it went to."""
    if save.view != SAVES:
        raise SaveError("Only a save in the list can be deleted.")
    title_dir = save.holder
    if not save.data.is_dir():
        raise SaveError(f"Save {save.name} is not there any more.")
    trash = _new_trash(user_dir, save.profile, save.title_id, save.name)
    try:
        move_all(_trash_moves(title_dir, save.name, trash))
    except SaveError:
        _remove_empty(trash)
        raise
    return trash


def restore(user_dir: Path, save: Save) -> None:
    """Puts a deleted save back. Refused when a save of that name is there again (delete that one first)."""
    if save.view != DELETED:
        raise SaveError("Only a deleted save can be restored.")
    target = live_place(user_dir, save)
    title_dir = target.parent
    meta_target = title_dir / save.meta.name
    if target.exists() or meta_target.exists():
        raise SaveError(f"A save named {save.name} is there now: delete it first.")
    title_dir.mkdir(parents=True, exist_ok=True)
    moves = [(save.data, target)]
    if save.meta.is_dir():
        moves.append((save.meta, meta_target))
    last_good, last_good_target = save.holder / "backup", last_good_copy(title_dir, save.name)
    if last_good.is_dir() and not last_good_target.exists():
        last_good_target.parent.mkdir(parents=True, exist_ok=True)
        moves.append((last_good, last_good_target))
    old_copy, old_target = save.holder / "backup-old", title_dir / ".backup" / save.name
    if old_copy.is_dir() and not old_target.exists():
        old_target.parent.mkdir(parents=True, exist_ok=True)
        moves.append((old_copy, old_target))
    move_all(moves)
    _remove_empty(save.holder)


def delete_for_good(user_dir: Path, save: Save) -> None:
    """Removes a deleted save and the backups made of it before it was deleted (a new save in that slot keeps
    its own). The one action that removes files."""
    trash_root = (user_dir / ROOTS[DELETED]).resolve()
    holder = save.holder.resolve()
    if save.view != DELETED or trash_root not in holder.parents:
        raise SaveError(f"{save.holder} is not a deleted save.")
    try:
        shutil.rmtree(holder)
    except OSError as error:
        raise SaveError(f"The save could not be removed: {error}") from error
    deleted_at = stamp_time(holder.name)
    for copy in _backups_of(user_dir, save):
        if stamp_time(copy.name) <= deleted_at:
            try:
                shutil.rmtree(copy)
            except OSError as error:
                raise SaveError(f"A backup of the save could not be removed: {error}") from error


def _backups_of(user_dir: Path, save: Save) -> list[Path]:
    root = user_dir / ROOTS[BACKUPS] / save.profile / save.title_id
    if not root.is_dir():
        return []
    return [p for p in root.iterdir() if p.is_dir() and STAMP.sub("", p.name) == save.name]


def restore_backup(user_dir: Path, save: Save) -> Path | None:
    """Puts a backup copy back in place of the save. The save there now goes to the deleted saves in the same
    step (returned), so nothing is lost; the backup itself stays."""
    if save.view != BACKUPS:
        raise SaveError("Only a backup can be restored here.")
    target = live_place(user_dir, save)
    title_dir = target.parent
    title_dir.mkdir(parents=True, exist_ok=True)
    # The copy is made first, beside the save (same drive), so the switch below is renames only.
    work = title_dir / f".restore-{save.name}-{_now_stamp()}"
    try:
        work.mkdir()
        shutil.copytree(save.data, work / save.name)
        if save.meta.is_dir():
            shutil.copytree(save.meta, work / save.meta.name)
    except OSError as error:
        shutil.rmtree(work, ignore_errors=True)
        raise SaveError(f"The backup could not be copied: {error}") from error
    trash = None
    moves: list[tuple[Path, Path]] = []
    if target.exists() or (title_dir / save.meta.name).exists():
        try:
            trash = _new_trash(user_dir, save.profile, save.title_id, save.name)
        except SaveError:
            shutil.rmtree(work, ignore_errors=True)  # only the copy made above
            raise
        moves = _trash_moves(title_dir, save.name, trash)
    moves.append((work / save.name, target))
    if (work / save.meta.name).is_dir():
        moves.append((work / save.meta.name, title_dir / save.meta.name))
    try:
        move_all(moves)
    except SaveError:
        if trash is not None:
            _remove_empty(trash)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)  # the copy, if it did not go in; never a player file
    return trash


# --- the home screen ------------------------------------------------------------------------------------------


def latest(found: list[Save], game: str) -> Save | None:
    """A game's newest save in a list from list_saves (newest first)."""
    return next((save for save in found if save.game == game), None)


def recent(found: list[Save], count: int) -> list[Save]:
    """The newest saves of all games, for the expedition log."""
    return found[:count]


def saved_at(save: Save) -> float:
    """When the save was made: the game's own stamp, else the save folder's time."""
    if save.time > 0:
        return save.time
    try:
        return save.data.stat().st_mtime
    except OSError:
        return 0.0


def when_text(stamp: float, now: float | None = None) -> str:
    """"today 14:02", "yesterday 21:30", "3 days ago", or the date of an older save; "" without a time."""
    if stamp <= 0:
        return ""
    then = time.localtime(stamp)
    today = time.localtime(time.time() if now is None else now)
    days = (date(today.tm_year, today.tm_mon, today.tm_mday) - date(then.tm_year, then.tm_mon, then.tm_mday)).days
    if days <= 0:
        return t("today {time}", time=time.strftime("%H:%M", then))
    if days == 1:
        return t("yesterday {time}", time=time.strftime("%H:%M", then))
    if days < 30:
        return t("{days} days ago", days=days)
    return f"{then.tm_mday} {time.strftime('%b %Y', then)}"
