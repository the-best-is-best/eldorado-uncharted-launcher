# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import config as cfg  # noqa: E402
from core import profiles  # noqa: E402


def load(tmp_path: Path, data: dict) -> cfg.Config:
    file = tmp_path / "launcher.json"
    file.write_text(json.dumps(data), encoding="utf-8")
    return cfg.Config.load(file)


def test_a_new_install_has_one_profile(tmp_path) -> None:
    config = load(tmp_path, {})
    assert profiles.all_profiles(config) == [profiles.Profile("1", "Player 1")]
    assert profiles.chosen(config).id == "1"


def test_older_settings_keep_their_save_profiles(tmp_path) -> None:
    config = load(tmp_path, {"games": {"u2": {"save_profile": "3"}}})
    assert [p.id for p in profiles.all_profiles(config)] == ["1", "3"]


def test_create_rename_and_choose(tmp_path) -> None:
    config = load(tmp_path, {})
    made = profiles.create(config, "  Michelle   R ")
    assert made == profiles.Profile("2", "Michelle R")
    stored = cfg.Config.load(config.file)
    assert stored.data["profile"] == "2"
    assert all(stored.game(key)["save_profile"] == "2" for key in ("u1", "u2", "u3"))
    profiles.rename(stored, "1", "Sara")
    profiles.choose(stored, "1")
    again = cfg.Config.load(config.file)
    assert [(p.id, p.name) for p in profiles.all_profiles(again)] == [("1", "Sara"), ("2", "Michelle R")]
    assert again.game("u3")["save_profile"] == "1"


def test_names_are_needed_and_kept_apart(tmp_path) -> None:
    config = load(tmp_path, {})
    profiles.create(config, "Sara")
    with pytest.raises(profiles.ProfileError):
        profiles.create(config, "sara")
    with pytest.raises(profiles.ProfileError):
        profiles.create(config, "   ")
    with pytest.raises(profiles.ProfileError):
        profiles.choose(config, "9")
