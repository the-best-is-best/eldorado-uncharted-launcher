# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from ui.gamepad import (  # noqa: E402
    REPEAT_DELAY, REPEAT_INTERVAL, STICK_PRESS, STICK_RELEASE, RepeatState, held_actions, primed, step,
)


def test_buttons_map_to_actions() -> None:
    held = held_actions(["a", "b", "y", "leftshoulder", "rightshoulder", "start", "x"], 0, 0)
    assert held == {"accept", "back", "remove", "previous", "next", "play"}


def test_dpad_maps_to_directions() -> None:
    assert held_actions(["dpup", "dpleft"], 0, 0) == {"up", "left"}


def test_stick_uses_its_stronger_axis() -> None:
    assert held_actions([], -STICK_PRESS - 1, 100) == {"left"}
    assert held_actions([], 100, STICK_PRESS + 1) == {"down"}
    assert held_actions([], STICK_PRESS - 1, 0) == frozenset()


def test_stick_lets_go_only_under_the_release_limit() -> None:
    between = (STICK_PRESS + STICK_RELEASE) // 2
    assert held_actions([], 0, -between) == frozenset()
    assert held_actions([], 0, -between, previous=frozenset({"up"})) == {"up"}
    assert held_actions([], 0, -(STICK_RELEASE - 1), previous=frozenset({"up"})) == frozenset()


def test_button_fires_once_per_press() -> None:
    actions, state = step(RepeatState(), frozenset({"accept"}), 0.0)
    assert actions == ["accept"]
    actions, state = step(state, frozenset({"accept"}), 5.0)
    assert actions == []
    actions, state = step(state, frozenset(), 5.1)
    actions, state = step(state, frozenset({"accept"}), 5.2)
    assert actions == ["accept"]


def test_direction_repeats_after_the_delay() -> None:
    down = frozenset({"down"})
    actions, state = step(RepeatState(), down, 0.0)
    assert actions == ["down"]
    actions, state = step(state, down, REPEAT_DELAY - 0.01)
    assert actions == []
    actions, state = step(state, down, REPEAT_DELAY)
    assert actions == ["down"]
    actions, state = step(state, down, REPEAT_DELAY + REPEAT_INTERVAL / 2)
    assert actions == []
    actions, state = step(state, down, REPEAT_DELAY + REPEAT_INTERVAL)
    assert actions == ["down"]


def test_new_direction_fires_at_once_and_old_one_stays_while_held() -> None:
    _, state = step(RepeatState(), frozenset({"up"}), 0.0)
    actions, state = step(state, frozenset({"up", "left"}), 0.1)
    assert actions == []  # still up, its delay not over
    actions, state = step(state, frozenset({"left"}), 0.2)
    assert actions == ["left"]


def test_primed_ignores_what_is_held_until_let_go() -> None:
    state = primed(frozenset({"accept", "down"}))
    actions, state = step(state, frozenset({"accept", "down"}), 100.0)
    assert actions == []
    actions, state = step(state, frozenset(), 100.1)
    actions, state = step(state, frozenset({"accept", "down"}), 100.2)
    assert actions == ["accept", "down"]
