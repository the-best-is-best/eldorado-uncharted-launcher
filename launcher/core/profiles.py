# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Players: named profiles, like PS4 users. Each has its own saves (savedata/<id>) in all three games; the chosen
one plays every game.

launcher.json: "profiles": [{"id": "1", "name": "Michelle"}, ...], "profile": "1" (the chosen one). The id is the
PS4 user number the engine gets (BB_USER_ID_<game>, 1 to 16): every game's "save_profile" follows the chosen
profile, so the start script and the saves screens read it as before."""
from __future__ import annotations

from dataclasses import dataclass

from . import config as cfg
from . import games

MAX_PROFILES = 16       # the engine's user numbers
NAME_LENGTH = 24
DEFAULT_NAME = "Player {number}"
# The player's messages (translated where they are shown).
NO_NAME = "Type a name for the profile."
SAME_NAME = "There is already a profile with that name."
NO_PROFILE = "There is no such profile."
TOO_MANY = "16 profiles at most."


class ProfileError(Exception):
    """A profile could not be made or renamed; the message is for the player."""


@dataclass(frozen=True)
class Profile:
    id: str
    name: str


def all_profiles(config: cfg.Config) -> list[Profile]:
    """Every profile: the stored ones, and one for each save profile a game already uses (older settings)."""
    stored = config.data.get("profiles")
    found: dict[str, str] = {}
    for entry in stored if isinstance(stored, list) else []:
        if isinstance(entry, dict) and _valid_id(str(entry.get("id"))):
            found.setdefault(str(entry["id"]), _clean(str(entry.get("name") or "")))
    for key in games.KEYS:
        number = str(config.game(key).get("save_profile") or "1")
        if _valid_id(number):
            found.setdefault(number, "")
    if not found:
        found["1"] = ""
    return [Profile(number, name or DEFAULT_NAME.format(number=number))
            for number, name in sorted(found.items(), key=lambda item: int(item[0]))]


def chosen(config: cfg.Config) -> Profile:
    profiles = all_profiles(config)
    wanted = str(config.data.get("profile") or config.game(games.KEYS[0]).get("save_profile") or "1")
    return next((profile for profile in profiles if profile.id == wanted), profiles[0])


def choose(config: cfg.Config, profile_id: str) -> Profile:
    """The profile every game plays from now on."""
    profile = next((p for p in all_profiles(config) if p.id == profile_id), None)
    if profile is None:
        raise ProfileError(NO_PROFILE)
    _store(config, all_profiles(config), profile.id)
    return profile


def create(config: cfg.Config, name: str) -> Profile:
    """A new profile with its own, empty saves; it becomes the chosen one."""
    name = _clean(name)
    if not name:
        raise ProfileError(NO_NAME)
    profiles = all_profiles(config)
    if any(p.name.casefold() == name.casefold() for p in profiles):
        raise ProfileError(SAME_NAME)
    free = next((str(n) for n in range(1, MAX_PROFILES + 1) if all(p.id != str(n) for p in profiles)), None)
    if free is None:
        raise ProfileError(TOO_MANY)
    profile = Profile(free, name)
    _store(config, profiles + [profile], free)
    return profile


def rename(config: cfg.Config, profile_id: str, name: str) -> Profile:
    name = _clean(name)
    if not name:
        raise ProfileError(NO_NAME)
    profiles = all_profiles(config)
    if any(p.name.casefold() == name.casefold() and p.id != profile_id for p in profiles):
        raise ProfileError(SAME_NAME)
    renamed = [Profile(p.id, name) if p.id == profile_id else p for p in profiles]
    _store(config, renamed, chosen(config).id)
    return next(p for p in renamed if p.id == profile_id)


def _store(config: cfg.Config, profiles: list[Profile], active: str) -> None:
    config.data["profiles"] = [{"id": p.id, "name": p.name} for p in profiles]
    config.data["profile"] = active
    for key in games.KEYS:
        config.game(key)["save_profile"] = active
    config.save()


def _valid_id(text: str) -> bool:
    return text.isdigit() and 1 <= int(text) <= MAX_PROFILES


def _clean(name: str) -> str:
    return " ".join(name.split())[:NAME_LENGTH]
