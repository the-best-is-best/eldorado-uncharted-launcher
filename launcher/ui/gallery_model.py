# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Gallery screen's data (context property `gallery`): one game's F12 screenshots, newest first; open one,
open the folder, move one to the Recycle Bin. Errors become `note` (shown on the screen)."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import config as cfg
from core import gallery, games


class GalleryModel(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._index = games.KEYS.index(cfg.Config.load().selected)
        self._shots: list[gallery.Shot] = []
        self._note = ""
        self._read()

    def _read(self) -> None:
        try:
            self._shots = gallery.shots(games.KEYS[self._index])
        except gallery.GalleryError as error:
            self._shots = []
            self._note = str(error)

    def _shot(self, index: int) -> gallery.Shot | None:
        return self._shots[index] if 0 <= index < len(self._shots) else None

    # --- what QML reads -----------------------------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def games(self) -> list[dict]:
        return [{"key": game.key, "number": game.number, "title": game.title} for game in games.GAMES]

    @Property(int, notify=changed)
    def gameIndex(self) -> int:
        return self._index

    @Property("QVariantList", notify=changed)
    def rows(self) -> list[dict]:
        return [{"url": QUrl.fromLocalFile(str(shot.path)).toString(), "name": shot.name, "label": shot.label()}
                for shot in self._shots]

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    # --- what QML calls -----------------------------------------------------------------------------------------

    @Slot(int)
    def setGame(self, index: int) -> None:
        if 0 <= index < len(games.GAMES) and index != self._index:
            self._index = index
            self._note = ""
            self._read()
            self.changed.emit()

    @Slot()
    def reload(self) -> None:
        self._note = ""
        self._read()
        self.changed.emit()

    @Slot(int)
    def open(self, index: int) -> None:
        shot = self._shot(index)
        if shot:
            self._run(lambda: gallery.open_path(shot.path), "")

    @Slot()
    def openFolder(self) -> None:
        self._run(lambda: gallery.open_folder(games.KEYS[self._index]), "")

    @Slot(int, result=bool)
    def remove(self, index: int) -> bool:
        """The screenshot to the Recycle Bin; True when it went."""
        shot = self._shot(index)
        if not shot:
            return False
        done = self._run(lambda: gallery.delete(shot), f"{shot.name} moved to the Recycle Bin.")
        self._read()
        self.changed.emit()
        return done

    def _run(self, action: Callable[[], object], done_note: str) -> bool:
        try:
            action()
        except gallery.GalleryError as error:
            self._note = str(error)
            self.changed.emit()
            return False
        if self._note != done_note:
            self._note = done_note
            self.changed.emit()
        return True
