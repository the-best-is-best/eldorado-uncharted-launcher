# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The players for QML (context property `profiles`): the named profiles, the one playing, and making, renaming
and choosing one. A change of player is `switched`: main.py has every screen read its saves again."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from core import config as cfg
from core import profiles
from core.i18n import t


class ProfileModel(QObject):
    changed = Signal()
    switched = Signal()
    message = Signal(str)

    @Property("QVariantList", notify=changed)
    def all(self) -> list[dict[str, Any]]:
        config = cfg.Config.load()
        active = profiles.chosen(config).id
        return [{"id": p.id, "name": self._shown(p), "active": p.id == active} for p in profiles.all_profiles(config)]

    @Property(str, notify=changed)
    def activeName(self) -> str:
        return self._shown(profiles.chosen(cfg.Config.load()))

    @Property(str, notify=changed)
    def activeId(self) -> str:
        return profiles.chosen(cfg.Config.load()).id

    @Slot(str)
    def choose(self, profile_id: str) -> None:
        if profile_id != self.activeId:
            self._do(lambda config: profiles.choose(config, profile_id), switched=True)

    @Slot(str)
    def create(self, name: str) -> None:
        self._do(lambda config: profiles.create(config, name), switched=True)

    @Slot(str, str)
    def rename(self, profile_id: str, name: str) -> None:
        self._do(lambda config: profiles.rename(config, profile_id, name), switched=False)

    def _do(self, change: Any, switched: bool) -> None:
        try:
            change(cfg.Config.load())
        except profiles.ProfileError as error:
            self.message.emit(t(str(error)))
            return
        except OSError as error:
            self.message.emit(t("Could not save the settings: {error}", error=error))
            return
        self.changed.emit()
        if switched:
            self.switched.emit()

    @staticmethod
    def _shown(profile: profiles.Profile) -> str:
        """A default name ("Player 2") in the launcher's language; a name the player typed as typed."""
        default = profiles.DEFAULT_NAME.format(number=profile.id)
        return t("Player {number}", number=profile.id) if profile.name == default else profile.name
