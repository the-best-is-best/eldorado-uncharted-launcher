# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Keyboard, mouse and controller bindings of a game, and their form in probe-uN.ini (key_map, mouse_map, pad_map),
which tools/probe_uncharted.py turns into the engine's input-uN.ini.

A binding is "key:<SDL key name>" or "mouse:<left|middle|right|x1|x2|wheel_up|wheel_down>"; an action has up to
two. Controller buttons use SDL's names. The map syntax is the runtime's: "action=name,..."; an action's first
entry replaces its sources of that kind, further entries add, and "action=" leaves it unbound."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SLOTS = 2
STICK_ACTIONS: tuple[str, ...] = ("ls_up", "ls_down", "ls_left", "ls_right", "rs_up", "rs_down", "rs_left",
                                  "rs_right")
# The groups shown on the Controls page: (title, ((action, label), ...)).
GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("MOVEMENT", (("ls_up", "Move forward"), ("ls_down", "Move back"), ("ls_left", "Move left"),
                  ("ls_right", "Move right"), ("rs_up", "Look up"), ("rs_down", "Look down"),
                  ("rs_left", "Look left"), ("rs_right", "Look right"), ("walk", "Walk / run (press to switch)"))),
    ("WEAPONS (D-PAD)", (("left", "Left"), ("right", "Right"), ("up", "Up"), ("down", "Down"))),
    ("ACTIONS", (("cross", "Jump, climb"), ("circle", "Cover, roll, drop"), ("square", "Melee"),
                 ("triangle", "Interact, pick up"), ("l2", "Aim"), ("r2", "Fire"),
                 ("l1", "Grenade (hold, release to throw)"), ("r1", "Reload"), ("l3", "Left stick press"),
                 ("r3", "Right stick press"), ("options", "Pause menu"), ("touchpad_left", "Touch left"),
                 ("touchpad_right", "Touch right"))),
)
DEFAULT_BINDINGS: dict[str, tuple[str, ...]] = {
    "ls_up": ("key:W",), "ls_down": ("key:S",), "ls_left": ("key:A",), "ls_right": ("key:D",),
    "rs_up": ("key:Up",), "rs_down": ("key:Down",), "rs_left": ("key:Left",), "rs_right": ("key:Right",),
    "left": ("key:1", "mouse:wheel_down"), "right": ("key:2", "mouse:wheel_up"), "up": ("key:3",),
    "down": ("key:4",),
    "cross": ("key:Space",), "circle": ("key:Left Ctrl",), "square": ("key:F",), "triangle": ("key:R",),
    "l2": ("mouse:right",), "r2": ("mouse:left",), "l1": ("key:Q", "mouse:x1"), "r1": ("key:E", "mouse:x2"),
    "l3": ("key:Left Shift",), "r3": ("key:V", "mouse:middle"), "options": ("key:Escape", "key:Return"),
    "touchpad_left": ("key:Tab",), "touchpad_right": ("key:Backspace",),
    # The engine's walk key (a press switches walking and running: walk_toggle=1, tools/probe_uncharted.py; its
    # own default Left Ctrl is Circle here). Wheels and valves need no keys: the
    # mouse turns the stick while their prompt is on screen.
    "walk": ("key:B",),
}
# Actions the engine added later: a stored set made before them gets their defaults only where no action has
# those keys yet.
LATER_ACTIONS: tuple[str, ...] = ("walk",)
# Controller buttons that can be rebound (the runtime's default map) and the ones that cannot.
PAD_DEFAULTS: dict[str, str] = {
    "cross": "a", "circle": "b", "square": "x", "triangle": "y", "l1": "leftshoulder", "r1": "rightshoulder",
    "l3": "leftstick", "r3": "rightstick", "options": "start", "touchpad_right": "back", "up": "dpup",
    "down": "dpdown", "left": "dpleft", "right": "dpright",
}
PAD_FIXED: dict[str, str] = {
    "l2": "lefttrigger", "r2": "righttrigger", "touchpad_left": "leftshoulder+back",
    **{action: "lstick" for action in STICK_ACTIONS[:4]}, **{action: "rstick" for action in STICK_ACTIONS[4:]},
    **{action: "lstick" for action in LATER_ACTIONS},
}
# SDL3's gamepad buttons, in its order.
PAD_BUTTONS: tuple[str, ...] = ("a", "b", "x", "y", "back", "guide", "start", "leftstick", "rightstick",
                                "leftshoulder", "rightshoulder", "dpup", "dpdown", "dpleft", "dpright", "misc1",
                                "paddle1", "paddle2", "paddle3", "paddle4", "touchpad")
# A button's name on an Xbox and on a PlayStation controller.
PAD_NAMES: dict[str, tuple[str, str]] = {
    "a": ("A", "Cross"), "b": ("B", "Circle"), "x": ("X", "Square"), "y": ("Y", "Triangle"),
    "back": ("View", "Share"), "guide": ("Guide", "PS"), "start": ("Menu", "Options"),
    "leftstick": ("LS", "L3"), "rightstick": ("RS", "R3"), "leftshoulder": ("LB", "L1"),
    "rightshoulder": ("RB", "R1"), "lefttrigger": ("LT", "L2"), "righttrigger": ("RT", "R2"),
    "dpup": ("D-pad up", "D-pad up"), "dpdown": ("D-pad down", "D-pad down"),
    "dpleft": ("D-pad left", "D-pad left"), "dpright": ("D-pad right", "D-pad right"),
    "misc1": ("Share", "Mute"), "paddle1": ("P1", "P1"), "paddle2": ("P2", "P2"), "paddle3": ("P3", "P3"),
    "paddle4": ("P4", "P4"), "touchpad": ("Touchpad", "Touchpad"), "lstick": ("L stick", "L stick"),
    "rstick": ("R stick", "R stick"), "leftshoulder+back": ("LB + View", "L1 + Share"),
}
MOUSE_BUTTONS: dict[str, str] = {"left": "Left mouse", "middle": "Middle mouse", "right": "Right mouse",
                                 "x1": "Mouse back", "x2": "Mouse forward", "wheel_up": "Wheel up",
                                 "wheel_down": "Wheel down"}
# Keys the game window keeps for itself: Insert opens the in-game menu, Left Alt frees the mouse.
RESERVED_KEYS: frozenset[str] = frozenset({"Insert", "Left Alt"})

PROMPT_STYLES: tuple[tuple[str, str], ...] = (("auto", "Auto"), ("keyboard", "Keyboard and mouse"),
                                              ("playstation", "PlayStation"), ("xbox", "Xbox"))
SENSITIVITIES: tuple[tuple[str, str], ...] = (("0.5", "0.5x"), ("0.75", "0.75x"), ("1.0", "1x"), ("1.5", "1.5x"),
                                              ("2.0", "2x"), ("3.0", "3x"), ("4.0", "4x"), ("5.0", "5x"))
AIM_FACTORS: tuple[tuple[str, str], ...] = (("0.5", "0.5x"), ("1.0", "1x"), ("2.0", "2x"), ("3.0", "3x"),
                                            ("5.0", "5x"), ("10.0", "10x"))
# The launcher.json keys the Controls page writes into the ini too, with their defaults.
CONTROL_DEFAULTS: dict[str, Any] = {"controls": None, "pad_controls": None, "mouse": True, "mouse_sens": "1.0",
                                    "mouse_invert": False, "prompts": "auto", "mouse_aim_sens": "1.0",
                                    "vibration": True}

Bindings = dict[str, list[str]]


def bindings(stored: Mapping[str, Any] | None) -> Bindings:
    """Every action's bindings: the stored ones over the defaults."""
    result = {action: list(default) for action, default in DEFAULT_BINDINGS.items()}
    for action, entries in (stored or {}).items():
        if action in result and isinstance(entries, (list, tuple)):
            result[action] = [entry for entry in entries if isinstance(entry, str) and entry][:SLOTS]
    if stored:
        taken = {entry for action, entries in result.items() if action in stored for entry in entries}
        for action in LATER_ACTIONS:
            if action not in stored:
                result[action] = [entry for entry in result[action] if entry not in taken]
    return result


def pad_buttons(stored: Mapping[str, Any] | None) -> dict[str, str | None]:
    """Every rebindable action's controller button (None: unbound)."""
    result: dict[str, str | None] = dict(PAD_DEFAULTS)
    for action, button in (stored or {}).items():
        if action in result:
            result[action] = button or None
    return result


def parse(spec: str | None) -> list[tuple[str, str]]:
    entries = []
    for entry in (spec or "").split(","):
        action, equals, name = entry.partition("=")
        if equals:
            entries.append((action.strip(), name.strip()))
    return entries


def key_and_mouse_maps(controls: Mapping[str, Any] | None) -> tuple[str, str]:
    """key_map and mouse_map: every action listed, so an unbound one loses the runtime's own default."""
    keys, mouse = [], []
    for action, entries in bindings(controls).items():
        names = [entry[4:] for entry in entries if entry.startswith("key:")]
        keys += [f"{action}={name}" for name in names] or [f"{action}="]
        if action not in STICK_ACTIONS:
            buttons = [entry[6:] for entry in entries if entry.startswith("mouse:")]
            mouse += [f"{action}={name}" for name in buttons] or [f"{action}="]
    return ",".join(keys), ",".join(mouse)


def pad_map(stored: Mapping[str, Any] | None) -> str:
    """pad_map: "" while every button is the default."""
    buttons = pad_buttons(stored)
    if buttons == PAD_DEFAULTS:
        return ""
    return ",".join(f"{action}={button or ''}" for action, button in buttons.items())


def to_ini(game: Mapping[str, Any]) -> dict[str, str]:
    """A game's controls as its ini keys."""
    keys, mouse = key_and_mouse_maps(game.get("controls"))

    def flag(name: str) -> str:
        return "1" if game.get(name, CONTROL_DEFAULTS[name]) else "0"

    return {"key_map": keys, "mouse_map": mouse, "pad_map": pad_map(game.get("pad_controls")),
            "mouse": flag("mouse"), "mouse_sens": str(game.get("mouse_sens", "1.0")),
            "mouse_invert": flag("mouse_invert"), "prompts": str(game.get("prompts", "auto")),
            "mouse_aim_sens": str(game.get("mouse_aim_sens", "1.0")), "vibration": flag("vibration")}


def from_ini(ini: Mapping[str, str]) -> dict[str, Any] | None:
    """A game's controls from its ini (the in-game menu changes them too) as launcher.json values; None while
    the ini has no bindings yet."""
    if not any(name in ini for name in ("key_map", "mouse_map", "pad_map")):
        return None
    controls = bindings(None)
    _apply(controls, ini.get("key_map"), "key:")
    _apply(controls, ini.get("mouse_map"), "mouse:")
    pad: dict[str, str | None] = dict(PAD_DEFAULTS)
    replaced = set()
    for action, name in parse(ini.get("pad_map")):
        if action in pad and action not in replaced:
            replaced.add(action)
            pad[action] = name or None
    result: dict[str, Any] = {
        "controls": {action: entries[:SLOTS] for action, entries in controls.items()},
        "pad_controls": {action: button for action, button in pad.items() if button != PAD_DEFAULTS[action]},
    }
    for name in ("mouse", "vibration"):
        if name in ini:
            result[name] = ini[name] != "0"
    if "mouse_invert" in ini:
        result["mouse_invert"] = ini["mouse_invert"] == "1"
    if "mouse_sens" in ini:
        result["mouse_sens"] = listed_factor(ini["mouse_sens"], SENSITIVITIES)
    if "mouse_aim_sens" in ini:
        result["mouse_aim_sens"] = listed_factor(ini["mouse_aim_sens"], AIM_FACTORS)
    if "prompts" in ini:
        result["prompts"] = ini["prompts"] if ini["prompts"] in dict(PROMPT_STYLES) else "auto"
    return result


def _apply(controls: Bindings, spec: str | None, prefix: str) -> None:
    replaced = set()
    for action, name in parse(spec):
        if action not in controls:
            continue
        if action not in replaced:
            replaced.add(action)
            controls[action] = [entry for entry in controls[action] if not entry.startswith(prefix)]
        if name:
            controls[action].append(prefix + name)


def listed_factor(text: str, options: tuple[tuple[str, str], ...]) -> str:
    """A factor as one of the options when it is one (the in-game menu sets any value)."""
    try:
        value = float(text)
    except ValueError:
        return "1.0"
    for option, _ in options:
        if abs(float(option) - value) < 0.005:
            return option
    return f"{value:g}"


def bind(controls: Mapping[str, Any] | None, action: str, slot: int, binding: str | None) -> Bindings:
    """The bindings with `binding` in an action's slot (None clears it). A key or button does one thing: it
    leaves the action that had it."""
    if action not in DEFAULT_BINDINGS or not 0 <= slot < SLOTS:
        raise ValueError(f"no binding slot {action} {slot}")
    if binding and action in STICK_ACTIONS and not binding.startswith("key:"):
        raise ValueError("Stick directions take keys; the mouse moves the camera by itself.")
    result = bindings(controls)
    if binding:
        for other, entries in result.items():
            if binding in entries and (other, entries.index(binding)) != (action, slot):
                entries.remove(binding)
    entries: list[str | None] = list(result[action])
    while len(entries) <= slot:
        entries.append(None)
    entries[slot] = binding
    result[action] = [entry for entry in entries if entry][:SLOTS]
    return result


def bind_pad(stored: Mapping[str, Any] | None, action: str, button: str | None) -> dict[str, str | None]:
    """The controller buttons (as stored: only those that differ from the defaults) with `button` on `action`.
    A button does one thing: the action that had it takes this action's old button."""
    if action not in PAD_DEFAULTS:
        raise ValueError(f"{action} has a fixed controller button")
    if button and button not in PAD_BUTTONS:
        raise ValueError(f"no controller button {button!r}")
    changed: dict[str, Any] = dict(stored or {})
    current = pad_buttons(changed)
    if button:
        for other, held in current.items():
            if held == button and other != action:
                changed[other] = current[action]
    changed[action] = button or ""
    return {name: held for name, held in pad_buttons(changed).items() if held != PAD_DEFAULTS[name]}


def label(binding: str | None) -> str:
    if not binding:
        return "—"
    kind, _, name = binding.partition(":")
    return MOUSE_BUTTONS.get(name, name) if kind == "mouse" else name


def pad_label(button: str | None, style: str, action: str = "") -> str:
    """A controller button's name in the prompt style (Auto and Keyboard name Xbox buttons)."""
    if not button:
        return "—"
    playstation = style == "playstation"
    if playstation and action in ("touchpad_left", "touchpad_right") and \
            button == PAD_DEFAULTS.get(action, PAD_FIXED.get(action)):
        # A PlayStation controller's touchpad click is both (the finger's side picks one).
        return "Touchpad left" if action == "touchpad_left" else "Touchpad right"
    names = PAD_NAMES.get(button)
    return names[1 if playstation else 0] if names else button
