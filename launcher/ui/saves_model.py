# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Saves screen's model (QML context property `saves`): the rows of one view (saves, deleted saves, backups),
the selected row, the delete/restore that waits for its second press, and a status line. core/saves.py does the
work; this turns its errors into the status line."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import art
from core import config as cfg
from core import game_files, games, paths, saves
from core.i18n import t

VIEW_NAMES: dict[str, str] = {saves.SAVES: "SAVES", saves.DELETED: "DELETED SAVES", saves.BACKUPS: "BACKUPS"}
# What each view does with OK and Delete; the ones in TWICE wait for a second press.
ACCEPT: dict[str, str] = {saves.DELETED: "restore", saves.BACKUPS: "restore_backup"}
REMOVE: dict[str, str] = {saves.SAVES: "delete", saves.DELETED: "delete_for_good"}
TWICE = {"delete", "delete_for_good", "restore_backup"}
ARMED_NOTES: dict[str, str] = {"delete": "PRESS DELETE AGAIN TO DELETE",
                               "delete_for_good": "PRESS DELETE AGAIN TO REMOVE FOR GOOD",
                               "restore_backup": "PRESS OK AGAIN TO RESTORE"}
# The texts below are English; t() reads them in the launcher's language where they are handed to QML.
# The key hints of each view (KeyHint.qml's actions), after "\u2190 \u2192 VIEWS".
ACCEPT_HINTS: dict[str, str] = {saves.DELETED: "RESTORE", saves.BACKUPS: "RESTORE (TWICE)"}
REMOVE_HINTS: dict[str, str] = {saves.SAVES: "DELETE (TWICE)", saves.DELETED: "REMOVE FOR GOOD (TWICE)"}


VIEW_LINES: dict[str, str] = {saves.SAVES: "Your saves of all three games.",
                              saves.DELETED: "Deleted saves are kept here until removed for good.",
                              saves.BACKUPS: "Copies made before each start, of the saves there now."}
# The game stores Arabic as presentation forms already in display order; Qt would reorder them right to left, so
# such text is shown inside a left-to-right override (as stored, as the released launcher showed it).
LTR_OVERRIDE, POP = "\u202d", "\u202c"


def shown(text: str) -> str:
    if not saves.is_presentation_text(text):
        return text
    return "\n".join(f"{LTR_OVERRIDE}{line}{POP}" for line in text.split("\n"))


def picture_url(path: Path | None) -> str:
    """A save picture's address for QML, with the file's version after it: Qt keeps images by address, and the
    game writes the same slot (the same file) again and again."""
    if path is None:
        return ""
    return f"{QUrl.fromLocalFile(str(path)).toString()}?{art.version_of(path)}"


def when(stamp: float) -> str:
    return time.strftime("%Y-%m-%d  %H:%M", time.localtime(stamp)) if stamp > 0 else ""


class SavesModel(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._view = saves.SAVES
        self._saves: list[saves.Save] = []
        self._index = 0
        self._armed = ""          # the action waiting for its second press on the selected row
        self._status = ""
        self._error = False
        self._game_running = False

    # --- what QML reads ---------------------------------------------------------------------------------------

    @Property("QVariantList", notify=changed)
    def rows(self) -> list[dict]:
        return [self._row(position, save) for position, save in enumerate(self._saves)]

    @Property(str, notify=changed)
    def view(self) -> str:
        return self._view

    @Property(str, notify=changed)
    def viewName(self) -> str:
        return t(VIEW_NAMES[self._view])

    @Property(str, notify=changed)
    def viewLine(self) -> str:
        return t(VIEW_LINES[self._view])

    @Property("QVariantList", notify=changed)
    def views(self) -> list[dict]:
        return [{"key": key, "name": t(VIEW_NAMES[key])} for key in saves.VIEWS]

    @Property(int, notify=changed)
    def selectedIndex(self) -> int:
        return self._index

    @Property(bool, notify=changed)
    def armed(self) -> bool:
        return bool(self._armed)

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def statusIsError(self) -> bool:
        return self._error

    @Property("QVariantList", notify=changed)
    def hints(self) -> list[dict[str, str]]:
        """The view's key hints, as KeyHint.qml takes them (the key cap follows the device in use)."""
        entries = [{"action": "views", "text": t("VIEWS")}]
        if self._view in ACCEPT_HINTS:
            entries.append({"action": "accept", "text": t(ACCEPT_HINTS[self._view])})
        if self._view in REMOVE_HINTS:
            entries.append({"action": "remove", "text": t(REMOVE_HINTS[self._view])})
        return entries

    def _get_game_running(self) -> bool:
        return self._game_running

    def _set_game_running(self, running: bool) -> None:
        if running != self._game_running:
            self._game_running = running
            self._disarm()
            self.changed.emit()

    # Set by the page from launcher.running: saves are not moved while the game may write them.
    gameRunning = Property(bool, _get_game_running, _set_game_running, notify=changed)

    # --- what QML calls ---------------------------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._load()
        self.changed.emit()

    @Slot(str)
    def setView(self, view: str) -> None:
        if view in saves.VIEWS and view != self._view:
            self._view = view
            self._index = 0
            self._disarm()
            self._say("")
            self._load()
            self.changed.emit()

    @Slot(int)
    def stepView(self, step: int) -> None:
        position = saves.VIEWS.index(self._view)
        self.setView(saves.VIEWS[(position + step) % len(saves.VIEWS)])

    @Slot(int)
    def select(self, index: int) -> None:
        if 0 <= index < len(self._saves) and index != self._index:
            self._index = index
            self._disarm()
            self.changed.emit()

    @Slot()
    def up(self) -> None:
        self.select(self._index - 1)

    @Slot()
    def down(self) -> None:
        self.select(self._index + 1)

    @Slot()
    def accept(self) -> None:
        self._act(ACCEPT.get(self._view, ""))

    @Slot()
    def remove(self) -> None:
        self._act(REMOVE.get(self._view, ""))

    @Slot()
    def disarm(self) -> None:
        if self._armed:
            self._disarm()
            self.changed.emit()

    # --- the work ---------------------------------------------------------------------------------------------

    def _profiles(self) -> dict[str, str]:
        config = cfg.Config.load()
        return {key: str(config.game(key).get("save_profile") or "1") for key in games.KEYS}

    def _load(self) -> None:
        try:
            # Saves of a newer game version than the copy chosen do not load in it: left out.
            version = game_files.version_in_use(cfg.Config.load())
            self._saves = saves.playable(saves.list_saves(paths.USER_DIR, self._view, self._profiles()), version)
        except OSError as error:
            self._saves = []
            self._say(t("The saves could not be read: {error}", error=error), error=True)
        self._index = max(0, min(self._index, len(self._saves) - 1))

    def _act(self, action: str) -> None:
        if not action or not self._saves:
            self.disarm()
            return
        if self._game_running:
            self._disarm()
            self._say(t("Close the game before changing its saves."), error=True)
            self.changed.emit()
            return
        if action in TWICE and self._armed != action:
            self._armed = action
            self.changed.emit()
            return
        self._disarm()
        save = self._saves[self._index]
        try:
            self._say(self._run(action, save))
        except saves.SaveError as error:
            self._say(str(error), error=True)
        self._load()
        self.changed.emit()

    def _run(self, action: str, save: saves.Save) -> str:
        """Does one action; returns the status line it leaves."""
        user_dir = paths.USER_DIR
        if action == "delete":
            saves.delete(user_dir, save)
            return t("{save} deleted (kept in Deleted saves).", save=save.name)
        if action == "restore":
            saves.restore(user_dir, save)
            return t("{save} restored.", save=save.name)
        if action == "delete_for_good":
            saves.delete_for_good(user_dir, save)
            return t("{save} removed for good.", save=save.name)
        replaced = saves.restore_backup(user_dir, save)
        if replaced:
            return t("{save} restored from the backup of {when} (the one it replaced is in Deleted saves).",
                     save=save.name, when=when(save.time))
        return t("{save} restored from the backup of {when}.", save=save.name, when=when(save.time))

    def _row(self, position: int, save: saves.Save) -> dict:
        game = games.by_key(save.game)
        note = t(ARMED_NOTES[self._armed]) if self._armed and position == self._index else \
            f"UNCHARTED {game.number}   {when(save.time)}"
        return {"name": save.name, "game": save.game, "gameName": game.name, "title": shown(save.chapter),
                # Shown as stored, the line runs from its sentence's end to its start: QML cuts it at the left.
                "backwards": saves.is_presentation_text(save.chapter),
                "detail": "   ".join(shown(line) for line in save.detail.split("\n")), "note": note,
                "picture": picture_url(save.picture)}

    def _disarm(self) -> None:
        self._armed = ""

    def _say(self, text: str, error: bool = False) -> None:
        self._status = text
        self._error = error
