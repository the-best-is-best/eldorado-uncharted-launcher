# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The controls of the three games: ONE shared set (ALL GAMES), and on top of it a game's own items.

An item is one key/mouse binding (an action's two slots), one controller button, or one of the mouse/controller
settings (mouse on/off, sensitivities, invert, prompts, vibration). A game that changes an item owns that item: the
other items keep following the shared set. Setting a game's item back to the shared value drops the ownership.

launcher.json:
  "shared_controls": {"controls": {action: [bindings]}, "pad_controls": {action: button|null}, "mouse": bool,
                      "mouse_sens": str, "mouse_invert": bool, "prompts": str, "mouse_aim_sens": str, "vibration": bool}
  "games": {"u2": {"own_controls": {"controls": {action: [...]}, "pad_controls": {action: button|null},
                                     "mouse_sens": "2.0"}, ...}}   # only the items the game owns
Each game entry also carries its EFFECTIVE values in the same fields the released launcher used ("controls",
"pad_controls", "mouse", ...): rewritten by apply() after every change, so the start script, the environment and old
tools keep reading them; the ini files (input_map.to_ini) are rewritten from them too.

The in-game menu writes the game's ini: sync_from_ini() takes a changed item as the player's wish for that game —
into the game's own items when it owns the item, else into the shared set (the games that follow it take it too)."""
from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from . import config as cfg
from . import games, input_map

SHARED = "shared_controls"
OWN = "own_controls"
ALL = "all"  # the scope of the shared set
SETTING_NAMES: tuple[str, ...] = ("mouse", "mouse_sens", "mouse_invert", "prompts", "mouse_aim_sens", "vibration")
KINDS = ("binding", "pad", "setting")


@dataclass
class ControlSet:
    """Every item with a value: the shared set, or what a game uses (shared with its own items on top)."""
    bindings: input_map.Bindings = field(default_factory=lambda: input_map.bindings(None))
    pad: dict[str, str | None] = field(default_factory=lambda: input_map.pad_buttons(None))
    settings: dict[str, Any] = field(default_factory=lambda: {name: input_map.CONTROL_DEFAULTS[name]
                                                              for name in SETTING_NAMES})

    def get(self, kind: str, name: str) -> Any:
        return {"binding": self.bindings, "pad": self.pad, "setting": self.settings}[kind][name]

    def put(self, kind: str, name: str, value: Any) -> None:
        if kind == "binding":
            self.bindings[name] = [entry for entry in value if isinstance(entry, str) and entry][:input_map.SLOTS]
        elif kind == "pad":
            self.pad[name] = value or None
        else:
            self.settings[name] = value

    def as_entry(self) -> dict[str, Any]:
        """The values in the released launcher's fields of a game entry."""
        return {"controls": copy.deepcopy(self.bindings), "pad_controls": dict(self.pad), **self.settings}

    @classmethod
    def from_entry(cls, entry: dict[str, Any] | None) -> ControlSet:
        entry = entry or {}
        settings = {name: entry.get(name, input_map.CONTROL_DEFAULTS[name]) for name in SETTING_NAMES}
        return cls(input_map.bindings(entry.get("controls")), input_map.pad_buttons(entry.get("pad_controls")),
                   settings)


@dataclass(frozen=True)
class Item:
    kind: str   # binding, pad or setting
    name: str   # the action, or the setting's name


# --- reading ------------------------------------------------------------------------------------------------------

def shared(config: cfg.Config) -> ControlSet:
    _migrate(config)
    return ControlSet.from_entry(config.data[SHARED])


def own(config: cfg.Config, key: str) -> dict[str, Any]:
    """A game's own items as stored: {"controls": {action: [...]}, "pad_controls": {action: button}, setting: value}."""
    _migrate(config)
    stored = config.game(key).get(OWN)
    if not isinstance(stored, dict):
        return {}
    result: dict[str, Any] = {}
    for table in ("controls", "pad_controls"):
        if isinstance(stored.get(table), dict):
            result[table] = {action: value for action, value in stored[table].items()
                             if action in (input_map.DEFAULT_BINDINGS if table == "controls" else input_map.PAD_DEFAULTS)}
    for name in SETTING_NAMES:
        if name in stored:
            result[name] = stored[name]
    return result


def own_items(config: cfg.Config, key: str) -> list[Item]:
    stored = own(config, key)
    items = [Item("binding", action) for action in stored.get("controls", {})]
    items += [Item("pad", action) for action in stored.get("pad_controls", {})]
    items += [Item("setting", name) for name in SETTING_NAMES if name in stored]
    return items


def effective(config: cfg.Config, key: str) -> ControlSet:
    """What the game uses: the shared set with its own items on top."""
    result = shared(config)
    stored = own(config, key)
    for action, entries in stored.get("controls", {}).items():
        result.put("binding", action, entries)
    for action, button in stored.get("pad_controls", {}).items():
        result.put("pad", action, button)
    for name in SETTING_NAMES:
        if name in stored:
            result.put("setting", name, stored[name])
    return result


def control_set(config: cfg.Config, scope: str) -> ControlSet:
    return shared(config) if scope == ALL else effective(config, games.by_key(scope).key)


# --- changing (each call saves launcher.json and rewrites the ini files) ---------------------------------------------

def set_item(config: cfg.Config, scope: str, item: Item, value: Any) -> None:
    """scope ALL: the shared value (a game that owns the item keeps its own). scope <game>: that game's own value,
    or back to following the shared set when the value is the shared one."""
    _change(config, scope, item, value)
    apply(config)


def set_binding(config: cfg.Config, scope: str, action: str, slot: int, binding: str | None) -> None:
    """One of an action's two slots; None clears it. A key or button does one thing: it leaves the action that
    had it (input_map.bind), and that action changes too."""
    current = control_set(config, scope).bindings
    _change_table(config, scope, "binding", current, input_map.bind(current, action, slot, binding))


def set_pad(config: cfg.Config, scope: str, action: str, button: str | None) -> None:
    """An action's controller button. A button does one thing: the action that had it takes this action's old
    button (input_map.bind_pad), so both actions change."""
    current = control_set(config, scope).pad
    stored = {name: held for name, held in current.items() if held != input_map.PAD_DEFAULTS[name]}
    _change_table(config, scope, "pad", current, input_map.pad_buttons(input_map.bind_pad(stored, action, button)))


def _change_table(config: cfg.Config, scope: str, kind: str, old: Mapping[str, Any], new: Mapping[str, Any]) -> None:
    for name, value in new.items():
        if value != old.get(name):
            _change(config, scope, Item(kind, name), value)
    apply(config)


def _change(config: cfg.Config, scope: str, item: Item, value: Any) -> None:
    if item.kind not in KINDS:
        raise KeyError(f"no control item kind {item.kind!r}")
    value = _clean(item, value)
    if scope == ALL:
        current = shared(config)
        current.put(item.kind, item.name, value)
        config.data[SHARED] = current.as_entry()
    else:
        key = games.by_key(scope).key
        if value == shared(config).get(item.kind, item.name):
            _drop_own(config, key, item)
        else:
            _store_own(config, key, item, value)


def clear_own(config: cfg.Config, key: str, item: Item | None = None) -> None:
    """One of a game's own items, or all of them, back to the shared set."""
    key = games.by_key(key).key
    if item is None:
        config.game(key)[OWN] = {}
    else:
        _drop_own(config, key, item)
    apply(config)


def make_shared(config: cfg.Config, key: str) -> None:
    """A game's controls become the shared set (its own items included); the game then follows it."""
    key = games.by_key(key).key
    config.data[SHARED] = effective(config, key).as_entry()
    config.game(key)[OWN] = {}
    apply(config)


def reset(config: cfg.Config, scope: str) -> None:
    """The defaults: for ALL, the shared set (own items stay); for a game, its own items are dropped."""
    if scope == ALL:
        config.data[SHARED] = ControlSet().as_entry()
        apply(config)
    else:
        clear_own(config, scope)


def sync_from_ini(config: cfg.Config, key: str) -> bool:
    """The game's ini as the in-game menu left it: every item that differs from what the game uses goes into the
    game's own items when it owns the item, else into the shared set. True when something changed."""
    key = games.by_key(key).key
    found = input_map.from_ini(cfg.read_ini(key))
    if found is None:
        apply(config, [key])
        return False
    ours, theirs = effective(config, key), ControlSet.from_entry(found)
    owned = set(own_items(config, key))
    changed = False
    for item in _all_items():
        new, old = theirs.get(item.kind, item.name), ours.get(item.kind, item.name)
        if new == old:
            continue
        changed = True
        if item in owned:
            _store_own(config, key, item, new)
        else:
            current = shared(config)
            current.put(item.kind, item.name, new)
            config.data[SHARED] = current.as_entry()
    apply(config)
    return changed


def apply(config: cfg.Config, keys: tuple[str, ...] | list[str] = games.KEYS) -> None:
    """Every game's effective values into its entry and its ini; launcher.json saved."""
    _migrate(config)
    for key in games.KEYS:
        config.game(key).update(effective(config, key).as_entry())
    config.save()
    for key in keys:
        cfg.write_ini(key, input_map.to_ini(config.game(key)))


# --- for the screen -------------------------------------------------------------------------------------------------

def differences_text(config: cfg.Config, key: str) -> str:
    """"Melee, Reload and Mouse sensitivity" — the items a game owns, by their labels."""
    labels = {action: label for _, actions in input_map.GROUPS for action, label in actions}
    names = []
    for item in own_items(config, key):
        if item.kind == "setting":
            names.append(SETTING_LABELS[item.name])
        else:
            names.append(labels.get(item.name, item.name) + (" (controller)" if item.kind == "pad" else ""))
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


SETTING_LABELS: dict[str, str] = {"mouse": "Mouse", "mouse_sens": "Mouse sensitivity", "mouse_invert": "Invert mouse",
                                  "prompts": "Button prompts", "mouse_aim_sens": "Aim sensitivity",
                                  "vibration": "Controller vibration"}


# --- inside ---------------------------------------------------------------------------------------------------------

def _most_common(current: dict[str, ControlSet], chosen: str) -> ControlSet:
    """The game's set that the fewest items of the other games differ from (ties: the chosen game, then order)."""
    def apart(base: ControlSet) -> int:
        return sum(1 for key in games.KEYS for item in _all_items()
                   if current[key].get(item.kind, item.name) != base.get(item.kind, item.name))

    order = [chosen] + [key for key in games.KEYS if key != chosen]
    return min((current[key] for key in order), key=apart)


def _all_items() -> list[Item]:
    return ([Item("binding", action) for action in input_map.DEFAULT_BINDINGS]
            + [Item("pad", action) for action in input_map.PAD_DEFAULTS]
            + [Item("setting", name) for name in SETTING_NAMES])


def _clean(item: Item, value: Any) -> Any:
    if item.kind == "binding":
        return [entry for entry in value if isinstance(entry, str) and entry][:input_map.SLOTS]
    if item.kind == "pad":
        return value or None
    if item.name in ("mouse", "mouse_invert", "vibration"):
        return bool(value)
    return str(value)


def _store_own(config: cfg.Config, key: str, item: Item, value: Any) -> None:
    stored = own(config, key)
    if item.kind == "binding":
        stored.setdefault("controls", {})[item.name] = list(value)
    elif item.kind == "pad":
        stored.setdefault("pad_controls", {})[item.name] = value
    else:
        stored[item.name] = value
    config.game(key)[OWN] = stored


def _drop_own(config: cfg.Config, key: str, item: Item) -> None:
    stored = own(config, key)
    table = {"binding": "controls", "pad": "pad_controls"}.get(item.kind)
    if table:
        stored.get(table, {}).pop(item.name, None)
        if table in stored and not stored[table]:
            del stored[table]
    else:
        stored.pop(item.name, None)
    config.game(key)[OWN] = stored


def _migrate(config: cfg.Config) -> None:
    """Once: settings from the released launcher (controls per game) or from the first shared-controls build (a
    whole-set "own_controls" switch). The shared set is the chosen game's controls (its ini included, as the
    released launcher read it); every other game keeps what differs as its own items. Nothing a player set is lost."""
    data = config.data
    migrated = isinstance(data.get(SHARED), dict) and all(
        isinstance(config.game(key).get(OWN), dict) for key in games.KEYS)
    if migrated:
        return
    current, configured = {}, {}
    for key in games.KEYS:
        entry = dict(config.game(key))
        found = input_map.from_ini(cfg.read_ini(key))
        # A game nobody ever set up (no ini, the defaults in its entry) simply follows the shared set.
        configured[key] = found is not None or any(
            entry.get(name) is not None and entry.get(name) != default
            for name, default in input_map.CONTROL_DEFAULTS.items())
        if found:
            entry.update(found)
        current[key] = ControlSet.from_entry(entry)
    if isinstance(data.get(SHARED), dict):
        base = ControlSet.from_entry(data[SHARED])
    else:
        # The shared set: the games' most common controls (two games alike, the third apart: the third keeps its
        # differences as its own), the chosen game's when they all differ.
        base = _most_common(current, config.selected)
    data[SHARED] = base.as_entry()
    for key in games.KEYS:
        game = config.game(key)
        # The first shared-controls build had a whole-set switch: off meant the game followed the shared set.
        keeps_own = configured[key] and game.get(OWN) is not False
        stored: dict[str, Any] = {}
        if keeps_own:
            for item in _all_items():
                value = current[key].get(item.kind, item.name)
                if value != base.get(item.kind, item.name):
                    if item.kind == "binding":
                        stored.setdefault("controls", {})[item.name] = list(value)
                    elif item.kind == "pad":
                        stored.setdefault("pad_controls", {})[item.name] = value
                    else:
                        stored[item.name] = value
        game[OWN] = stored
    for key in games.KEYS:
        config.game(key).update(effective(config, key).as_entry())
    config.save()
    for key in games.KEYS:
        cfg.write_ini(key, input_map.to_ini(config.game(key)))
