# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""The game with its update (an extracted .pkg, e.g. a translation or update 1.0x) laid over it.

The engine reads one game folder (BB_GAME_DIR). When an update folder is found, a view is made: a folder of links
to the game's files, with the update's files in place of the game's (names compared without case). Neither the game
nor the update is changed; the view costs a handful of links and is kept while both folders stay the same
(view_stamp).

The update is UNCHARTED_UPDATE (a folder, or 0 for none), else a folder next to the game folder named like it plus
-patch / -update (for example "Game-patch"), with or without uroot. An update holds eboot.bin and sce_sys/param.sfo.
"""
import os
import shutil
import stat
from pathlib import Path

UPDATE_SUFFIXES = ("-patch", "-update", "_patch", "_update")
VIEW_NAME = "game-with-update"
LAST_VIEW = ""  # "kept" or "made" by the last build_view (the start script logs it)


def is_update_dir(folder):
    return (folder / "eboot.bin").is_file() and (folder / "sce_sys" / "param.sfo").is_file()


def find_update(game_dir):
    """The update folder for game_dir, or None."""
    chosen = os.environ.get("UNCHARTED_UPDATE", "")
    if chosen == "0":
        return None
    if chosen:
        candidates = [Path(chosen), Path(chosen) / "uroot"]
    else:
        title = game_dir.parent if game_dir.name.lower() == "uroot" else game_dir
        names = {title.name.lower() + suffix for suffix in UPDATE_SUFFIXES}
        try:
            siblings = [entry for entry in title.parent.iterdir() if entry.name.lower() in names]
        except OSError:
            siblings = []
        candidates = [path for entry in siblings for path in (entry / "uroot", entry)]
    for candidate in candidates:
        if is_update_dir(candidate):
            return candidate.resolve()
    if chosen:
        print(f"Update: {chosen} holds no eboot.bin and sce_sys/param.sfo; starting without it", flush=True)
    return None


def is_link(path):
    """A symlink or a junction (never followed when the view is removed)."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def link(path, target):
    """path -> target: a symlink, else a junction (folders) or a hard link (files; a copy across drives)."""
    try:
        path.symlink_to(target, target_is_directory=target.is_dir())
        return
    except OSError:
        if os.name != "nt":
            raise
    if target.is_dir():
        import _winapi
        _winapi.CreateJunction(str(target), str(path))
        return
    try:
        os.link(target, path)
    except OSError:
        shutil.copy2(target, path)


def remove_view(path):
    """Deletes a view. Links are removed as links: nothing inside the game or the update is touched."""
    if is_link(path):
        if path.is_dir():
            os.rmdir(path)
        else:
            path.unlink()
    elif path.is_dir():
        for child in list(path.iterdir()):
            remove_view(child)
        path.rmdir()
    elif path.exists():
        path.unlink()  # a hard link or a copy: the game's own file keeps its other name


def lay_over(update, view):
    """Puts update's entries into view: files replace view's, folders both have are merged."""
    entries = {entry.name.casefold(): entry for entry in view.iterdir()}
    for item in update.iterdir():
        match = entries.get(item.name.casefold(), view / item.name)
        if item.is_dir() and match.is_dir():
            if is_link(match):  # a linked game folder: becomes a real folder of links, then merged
                inner = match.resolve(strict=True)
                remove_view(match)
                match.mkdir()
                for child in inner.iterdir():
                    link(match / child.name, child)
            lay_over(item, match)
        else:
            if match.exists() or is_link(match):
                remove_view(match)
            link(match, item)


def view_stamp(game_dir, update):
    """What the view is made of: both folders, and the times of every folder lay_over merges (the update's
    folders and the game's folders of the same names). A file added, removed or replaced changes its folder's
    time; one rewritten in place is the same file the view links to."""
    lines = [f"game {game_dir.resolve()}", f"update {update.resolve()}"]

    def walk(update_dir, game_side, rel):
        lines.append(f"u {rel} {update_dir.stat().st_mtime_ns}")
        if game_side is not None and game_side.is_dir():
            lines.append(f"g {rel} {game_side.stat().st_mtime_ns}")
        game_entries = {}
        if game_side is not None and game_side.is_dir():
            game_entries = {entry.name.casefold(): entry for entry in game_side.iterdir()}
        for item in sorted(update_dir.iterdir(), key=lambda entry: entry.name.casefold()):
            if item.is_dir():
                walk(item, game_entries.get(item.name.casefold()), f"{rel}/{item.name}")

    walk(update, game_dir, ".")
    return "\n".join(lines) + "\n"


def build_view(game_dir, update, place):
    """The view of game_dir with update over it, in place/VIEW_NAME. Kept from the last start while its stamp
    (view_stamp) is the same: making it again took 2-6 s (4,913 links) at every start."""
    view = place / VIEW_NAME
    stamp_file = place / (VIEW_NAME + ".stamp")
    try:
        stamp = view_stamp(game_dir, update)
    except OSError:
        stamp = None
    if stamp and view.is_dir() and not is_link(view) and (view / "eboot.bin").exists():
        try:
            if stamp_file.read_text(encoding="utf-8") == stamp:
                global LAST_VIEW
                LAST_VIEW = "kept"
                return view
        except OSError:
            pass
    if stamp_file.exists():
        stamp_file.unlink()
    if view.exists() or is_link(view):
        remove_view(view)
    view.mkdir(parents=True)
    try:
        for entry in game_dir.iterdir():
            link(view / entry.name, entry)
        lay_over(update, view)
    except BaseException:
        remove_view(view)
        raise
    if stamp:
        stamp_file.write_text(stamp, encoding="utf-8")
    globals()["LAST_VIEW"] = "made"
    return view


def game_with_update(game_dir, views_dir):
    """The folder the engine should read: a view when an update is found, else game_dir itself."""
    update = find_update(game_dir)
    if not update:
        return game_dir
    if update == game_dir or update in game_dir.parents or game_dir in update.parents:
        print(f"Update: {update} is inside the game folder; starting without it", flush=True)
        return game_dir
    places = [views_dir]
    if Path(game_dir.anchor).resolve() != Path(views_dir.anchor).resolve():
        places.insert(0, game_dir.parent / ".eldorado-views")  # file links can't cross drives
    for place in places:
        try:
            view = build_view(game_dir, update, place)
            print(f"Update: {update} laid over the game ({view})", flush=True)
            return view
        except OSError as error:
            print(f"Update: view in {place} failed ({error})", flush=True)
    print("Update: could not combine the game and its update; starting without it", flush=True)
    return game_dir
