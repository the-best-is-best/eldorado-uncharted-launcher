# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Trophies screen's data (context property `trophies`): one game's set at a time, plus each game's percent
for the home screen. Sets are read once and kept; reload() reads the unlocks again (after a game ran)."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core import config as cfg
from core import games, trophies


class TrophiesModel(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._index = games.KEYS.index(cfg.Config.load().selected)
        self._sets: dict[str, trophies.TrophySet | None] = {}
        self._errors: dict[str, str] = {}
        self._engine = None
        self._migrated = False

    # --- reading ------------------------------------------------------------------------------------------------

    def _set(self, key: str) -> trophies.TrophySet | None:
        if key not in self._sets:
            self._sets[key] = self._read(key)
        return self._sets[key]

    def _read(self, key: str) -> trophies.TrophySet | None:
        config = cfg.Config.load()
        try:
            if not self._migrated:
                self._migrated = True
                trophies.migrate_old_logs()
            self._engine = self._engine or trophies.load_engine()
            language = trophies.language_number(config.game(key).get("language", "1"))
            self._errors.pop(key, None)
            return trophies.load(key, config.game_dir(), language, engine=self._engine)
        except (trophies.TrophyError, OSError) as error:
            self._errors[key] = str(error)
            return None

    @property
    def _key(self) -> str:
        return games.KEYS[self._index]

    # --- what QML reads -----------------------------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def games(self) -> list[dict]:
        return [{"key": game.key, "number": game.number, "title": game.title} for game in games.GAMES]

    @Property(int, notify=changed)
    def gameIndex(self) -> int:
        return self._index

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._set(self._key) is not None

    @Property(str, notify=changed)
    def note(self) -> str:
        """Why there is no list (shown instead of it)."""
        if self._set(self._key) is not None:
            return ""
        return self._errors.get(self._key) or \
            "No trophy list: the game folder has no sce_sys/trophy pack for this game."

    @Property(int, notify=changed)
    def count(self) -> int:
        current = self._set(self._key)
        return current.count if current else 0

    @Property(int, notify=changed)
    def total(self) -> int:
        current = self._set(self._key)
        return len(current.trophies) if current else 0

    @Property(int, notify=changed)
    def progress(self) -> int:
        current = self._set(self._key)
        return current.percent if current else 0

    @Property("QVariantList", notify=changed)
    def grades(self) -> list[dict]:
        current = self._set(self._key)
        return [{"grade": g.grade, "name": g.name, "earned": g.earned, "total": g.total}
                for g in (current.grades() if current else [])]

    @Property("QVariantList", notify=changed)
    def rows(self) -> list[dict]:
        current = self._set(self._key)
        if not current:
            return []
        return [{"number": t.number, "grade": t.grade, "gradeName": trophies.GRADE_NAMES.get(t.grade, "BRONZE"),
                 "name": t.shown_name(), "detail": t.shown_detail(),
                 "earned": bool(t.earned), "when": t.earned_text(), "secret": t.secret,
                 "icon": QUrl.fromLocalFile(str(t.icon)).toString() if t.icon else ""}
                for t in current.trophies]

    @Property("QVariantMap", notify=changed)
    def percents(self) -> dict[str, int]:
        """Each game's percent (-1 without a list), for the home screen."""
        return {key: self.percent(key) for key in games.KEYS}

    # --- what QML calls -----------------------------------------------------------------------------------------

    @Slot(str, result=int)
    def percent(self, key: str) -> int:
        current = self._set(key) if key in games.KEYS else None
        return current.percent if current else -1

    @Slot(int)
    def setGame(self, index: int) -> None:
        if 0 <= index < len(games.GAMES) and index != self._index:
            self._index = index
            self.changed.emit()

    @Slot()
    def reload(self) -> None:
        """Reads every set again (new unlocks, a changed game folder or language)."""
        self._sets.clear()
        self.changed.emit()
