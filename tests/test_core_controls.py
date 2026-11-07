# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import config as cfg  # noqa: E402
from core import controls, input_map, paths  # noqa: E402

Item = controls.Item


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "USER_DIR", tmp_path / "user")
    return tmp_path


def load(home: Path, text: str = '{"game": "u1"}') -> cfg.Config:
    file = home / "launcher.json"
    file.write_text(text, encoding="utf-8")
    return cfg.Config.load(file)


def ini(home: Path, key: str) -> dict[str, str]:
    return cfg.read_ini(key)


def test_a_shared_change_reaches_every_game(home) -> None:
    config = load(home)
    controls.set_binding(config, controls.ALL, "square", 0, "key:G")
    for key in ("u1", "u2", "u3"):
        assert controls.effective(config, key).bindings["square"][0] == "key:G"
        assert "square=G" in ini(home, key)["key_map"]
        assert controls.own_items(config, key) == []


def test_a_games_change_is_its_own_and_follows_the_rest(home) -> None:
    config = load(home)
    controls.set_binding(config, "u2", "square", 0, "key:G")
    assert controls.effective(config, "u2").bindings["square"][0] == "key:G"
    assert controls.effective(config, "u1").bindings["square"][0] == "key:F"
    assert controls.own_items(config, "u2") == [Item("binding", "square")]
    # Other keys of U2 still follow the shared set.
    controls.set_binding(config, controls.ALL, "triangle", 0, "key:T")
    assert controls.effective(config, "u2").bindings["triangle"][0] == "key:T"
    assert controls.effective(config, "u2").bindings["square"][0] == "key:G"
    # Back to the shared value drops the ownership.
    controls.set_binding(config, "u2", "square", 0, "key:F")
    assert controls.own_items(config, "u2") == []


def test_settings_and_pad_buttons_are_items_too(home) -> None:
    config = load(home)
    controls.set_item(config, "u3", Item("setting", "mouse_sens"), "2.0")
    controls.set_item(config, "u3", Item("pad", "cross"), "b")
    assert controls.effective(config, "u3").settings["mouse_sens"] == "2.0"
    assert controls.effective(config, "u1").settings["mouse_sens"] == "1.0"
    assert ini(home, "u3")["mouse_sens"] == "2.0" and ini(home, "u1")["mouse_sens"] == "1.0"
    assert "cross=b" in ini(home, "u3")["pad_map"]
    assert set(controls.own_items(config, "u3")) == {Item("setting", "mouse_sens"), Item("pad", "cross")}
    assert controls.differences_text(config, "u3") in ("Jump, climb (controller) and Mouse sensitivity",
                                                       "Mouse sensitivity and Jump, climb (controller)")
    controls.clear_own(config, "u3")
    assert controls.own_items(config, "u3") == []
    assert ini(home, "u3")["mouse_sens"] == "1.0"


def test_make_shared_takes_a_games_keys_to_all(home) -> None:
    config = load(home)
    controls.set_binding(config, "u1", "r1", 0, "key:E")
    controls.set_binding(config, "u1", "r1", 1, "mouse:x2")
    controls.make_shared(config, "u1")
    assert controls.own_items(config, "u1") == []
    assert controls.effective(config, "u3").bindings["r1"] == ["key:E", "mouse:x2"]


def test_the_in_game_menu_changes_the_shared_set_unless_the_game_owns_the_item(home) -> None:
    config = load(home)
    controls.set_item(config, "u2", Item("setting", "mouse_sens"), "2.0")
    # The in-game menu of U2 changes the melee key and its sensitivity.
    cfg.write_ini("u2", {"key_map": ini(home, "u2")["key_map"].replace("square=F", "square=H"), "mouse_sens": "3.0"})
    assert controls.sync_from_ini(config, "u2")
    assert controls.effective(config, "u1").bindings["square"][0] == "key:H"   # shared: the others took it
    assert controls.effective(config, "u2").settings["mouse_sens"] == "3.0"     # owned: U2 alone
    assert controls.effective(config, "u1").settings["mouse_sens"] == "1.0"
    assert not controls.sync_from_ini(config, "u2")


def test_released_launcher_settings_keep_every_games_controls(home) -> None:
    # The released launcher: controls per game, with U2's melee on G and its sensitivity 2x.
    config = load(home, json.dumps({"game": "u1", "games": {"u2": {"controls": {"square": ["key:G"]},
                                                                     "mouse_sens": "2.0"}}}))
    assert controls.effective(config, "u1").bindings["square"] == ["key:F"]
    assert controls.effective(config, "u2").bindings["square"] == ["key:G"]
    assert controls.effective(config, "u2").settings["mouse_sens"] == "2.0"
    assert set(controls.own_items(config, "u2")) == {Item("binding", "square"), Item("setting", "mouse_sens")}
    assert controls.own_items(config, "u1") == [] and controls.own_items(config, "u3") == []
    # The ini of each game holds what it uses.
    assert "square=G" in ini(home, "u2")["key_map"] and "square=F" in ini(home, "u1")["key_map"]


def test_first_shared_build_settings_migrate(home) -> None:
    # The whole-set switch: U3 own (its keys kept), U1 following the shared set.
    config = load(home, json.dumps({"game": "u1", "shared_controls": {"mouse_sens": "1.5"},
                                    "games": {"u1": {"own_controls": False, "mouse_sens": "1.5"},
                                              "u3": {"own_controls": True, "mouse_sens": "0.5"}}}))
    assert controls.effective(config, "u3").settings["mouse_sens"] == "0.5"
    assert controls.effective(config, "u1").settings["mouse_sens"] == "1.5"
    assert controls.own_items(config, "u3") == [Item("setting", "mouse_sens")]


def test_the_ini_of_an_old_install_is_read_once(home) -> None:
    # Before anything is stored, a game's ini (the old launcher wrote it) is what the game uses.
    config = load(home)
    cfg.write_ini("u1", input_map.to_ini({"controls": {"cross": ["key:J"]}}))
    cfg.write_ini("u2", input_map.to_ini({"controls": {"cross": ["key:K"]}}))
    assert controls.effective(config, "u1").bindings["cross"] == ["key:J"]   # the chosen game: the shared set
    assert controls.effective(config, "u2").bindings["cross"] == ["key:K"]   # its own
    assert controls.effective(config, "u3").bindings["cross"] == ["key:J"]   # follows the shared set


def test_the_shared_set_is_the_games_most_common_controls(home) -> None:
    # The released launcher left U1 apart (its own keys) and U2/U3 alike: the shared set is U2/U3's, U1 keeps its
    # differences as its own, even though U1 is the chosen game.
    config = load(home, json.dumps({"game": "u1", "games": {
        "u1": {"controls": {"square": ["key:C"], "triangle": ["key:E"]}, "prompts": "keyboard"},
        "u2": {"controls": {"square": ["key:F"], "triangle": ["key:R"]}, "prompts": "keyboard"},
        "u3": {"controls": {"square": ["key:F"], "triangle": ["key:R"]}, "prompts": "keyboard"}}}))
    assert controls.shared(config).bindings["square"] == ["key:F"]
    assert set(controls.own_items(config, "u1")) == {Item("binding", "square"), Item("binding", "triangle")}
    assert controls.own_items(config, "u2") == [] and controls.own_items(config, "u3") == []
