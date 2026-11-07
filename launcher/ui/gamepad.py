# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Controller input for the launcher's window: SDL3 through ctypes (Qt 6 has no gamepad module; the engine ships
SDL3.dll in gow3_pc/bin or gow3_pc/out). Only the gamepad subsystem is started, no SDL window.

How Main.qml uses it (main.py sets the context property: setContextProperty("gamepad", Gamepad())):

    Connections {
        target: gamepad
        function onAction(name) {
            // "up" "down" "left" "right" "accept" "remove" -> window.call(name)
            // "back" -> as Esc, "next"/"previous" -> as Tab/Shift+Tab, "play" -> start the selected game
        }
    }
    Keys.onPressed: gamepad.keyboardUsed()      // key hints follow the device used last
    KeyHint { device: gamepad.device }          // "keyboard", "xbox" or "playstation"

While a game runs the launcher calls gamepad.setActive(false) (the timer stops: no cost) and setActive(true) when
it is back; buttons still held at that moment are ignored until released. Input is read only while the
application has the focus.
"""
from __future__ import annotations

import ctypes
import math
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core import paths

# SDL_GamepadButton (SDL3) indexes of the buttons the launcher uses.
SDL_BUTTONS = {"a": 0, "b": 1, "y": 3, "start": 6, "leftshoulder": 9, "rightshoulder": 10,
               "dpup": 11, "dpdown": 12, "dpleft": 13, "dpright": 14}
BUTTON_ACTIONS = {"a": "accept", "b": "back", "y": "remove", "leftshoulder": "previous",
                  "rightshoulder": "next", "start": "play",
                  "dpup": "up", "dpdown": "down", "dpleft": "left", "dpright": "right"}
DIRECTIONS = ("up", "down", "left", "right")
SDL_INIT_GAMEPAD = 0x2000
SDL_AXIS_LEFTX, SDL_AXIS_LEFTY = 0, 1
PLAYSTATION_TYPES = (4, 5, 6)  # SDL_GAMEPAD_TYPE_PS3, PS4, PS5

# The stick counts as pushed past STICK_PRESS and as let go under STICK_RELEASE (no flicker at the edge).
STICK_PRESS = 16000
STICK_RELEASE = 12000
REPEAT_DELAY = 0.40  # seconds a direction is held before it repeats
REPEAT_INTERVAL = 0.12
POLL_MS = 16


def held_actions(buttons: Iterable[str], stick_x: int, stick_y: int,
                 previous: frozenset[str] = frozenset()) -> frozenset[str]:
    """The actions held now: mapped buttons plus the left stick as a direction (its stronger axis only; SDL's
    y grows downwards)."""
    held = {BUTTON_ACTIONS[name] for name in buttons if name in BUTTON_ACTIONS}
    stick_dirs = {d for d in DIRECTIONS if d in previous}
    if abs(stick_x) >= abs(stick_y):
        value, negative, positive = stick_x, "left", "right"
    else:
        value, negative, positive = stick_y, "up", "down"
    direction = negative if value < 0 else positive
    limit = STICK_RELEASE if direction in stick_dirs else STICK_PRESS
    if abs(value) >= limit:
        held.add(direction)
    return frozenset(held)


@dataclass(frozen=True)
class RepeatState:
    held: frozenset[str] = field(default_factory=frozenset)
    direction: str | None = None
    next_at: float = 0.0


def primed(held: frozenset[str]) -> RepeatState:
    """A state that ignores what is held now (until it is let go), for the moment input starts again."""
    direction = next((d for d in DIRECTIONS if d in held), None)
    return RepeatState(held, direction, math.inf)


def step(state: RepeatState, held: frozenset[str], now: float) -> tuple[list[str], RepeatState]:
    """The actions to send for what is held at `now`: buttons on their press, one direction on its press and
    then again after REPEAT_DELAY every REPEAT_INTERVAL."""
    actions = [a for a in sorted(held - state.held) if a not in DIRECTIONS]
    direction = state.direction if state.direction in held else next((d for d in DIRECTIONS if d in held), None)
    next_at = state.next_at
    if direction is None:
        next_at = 0.0
    elif direction != state.direction or direction not in state.held:
        actions.append(direction)
        next_at = now + REPEAT_DELAY
    elif now >= next_at:
        actions.append(direction)
        next_at = now + REPEAT_INTERVAL
    return actions, RepeatState(held, direction, next_at)


def sdl_candidates() -> list[Path]:
    msys = Path(os.environ.get("MSYS2_ROOT", "C:/msys64"))
    return [paths.ROOT / "gow3_pc" / "bin" / "SDL3.dll", paths.ROOT / "gow3_pc" / "out" / "SDL3.dll",
            msys / "clang64" / "bin" / "SDL3.dll"]


class _Sdl:
    """The few SDL3 calls the launcher needs, with their C types."""

    def __init__(self, library: ctypes.CDLL) -> None:
        lib = library
        lib.SDL_SetHint.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.SDL_SetHint.restype = ctypes.c_bool
        lib.SDL_Init.argtypes = [ctypes.c_uint32]
        lib.SDL_Init.restype = ctypes.c_bool
        lib.SDL_GetGamepads.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.SDL_GetGamepads.restype = ctypes.POINTER(ctypes.c_uint32)
        lib.SDL_OpenGamepad.argtypes = [ctypes.c_uint32]
        lib.SDL_OpenGamepad.restype = ctypes.c_void_p
        lib.SDL_CloseGamepad.argtypes = [ctypes.c_void_p]
        lib.SDL_GetGamepadButton.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.SDL_GetGamepadButton.restype = ctypes.c_bool
        lib.SDL_GetGamepadAxis.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.SDL_GetGamepadAxis.restype = ctypes.c_int16
        lib.SDL_GetGamepadType.argtypes = [ctypes.c_void_p]
        lib.SDL_GetGamepadType.restype = ctypes.c_int
        lib.SDL_free.argtypes = [ctypes.c_void_p]
        self.lib = lib

    @classmethod
    def load(cls, candidates: Iterable[Path]) -> _Sdl | None:
        for path in candidates:
            if not path.is_file():
                continue
            try:
                sdl = cls(ctypes.CDLL(str(path)))
            except (OSError, AttributeError):
                continue
            # No SDL window: controller input must arrive anyway.
            sdl.lib.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
            return sdl if sdl.lib.SDL_Init(SDL_INIT_GAMEPAD) else None
        return None

    def gamepad_ids(self) -> list[int]:
        self.lib.SDL_PumpEvents()  # hot-plug is seen through events
        count = ctypes.c_int(0)
        ids = self.lib.SDL_GetGamepads(ctypes.byref(count))
        if not ids:
            return []
        current = [ids[i] for i in range(count.value)]
        self.lib.SDL_free(ctypes.cast(ids, ctypes.c_void_p))
        return current


class Gamepad(QObject):
    """Sends action(name) for controller input; `device` says which device the key hints show."""

    action = Signal(str)
    deviceChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._sdl = _Sdl.load(sdl_candidates())
        self._pads: dict[int, int] = {}  # joystick id -> SDL_Gamepad pointer
        self._held: frozenset[str] = frozenset()
        self._state = RepeatState()
        self._resumed = True
        self._device = "keyboard"
        self._clock = time.monotonic
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)
        if self._sdl is not None:
            self._timer.start()

    def _get_device(self) -> str:
        return self._device

    def _set_device(self, device: str) -> None:
        if device != self._device:
            self._device = device
            self.deviceChanged.emit()

    device = Property(str, _get_device, notify=deviceChanged)

    def _get_available(self) -> bool:
        return self._sdl is not None

    available = Property(bool, _get_available, constant=True)

    @Slot(bool)
    def setActive(self, active: bool) -> None:
        if self._sdl is None:
            return
        if active and not self._timer.isActive():
            self._resumed = True
            self._timer.start()
        elif not active:
            self._timer.stop()

    @Slot()
    def keyboardUsed(self) -> None:
        self._set_device("keyboard")

    def _poll(self) -> None:
        app = QGuiApplication.instance()
        if app is not None and QGuiApplication.applicationState() != Qt.ApplicationState.ApplicationActive:
            self._resumed = True  # back in focus: what is held then does not count
            return
        held, pad = self.read()
        if self._resumed:
            self._resumed = False
            self._state = primed(held)
            return
        actions, self._state = step(self._state, held, self._clock())
        if actions and pad is not None:
            self._set_device(self._style(pad))
        for name in actions:
            self.action.emit(name)

    def read(self) -> tuple[frozenset[str], int | None]:
        """The actions held on all connected pads, and the pad that holds one (for the hints' style)."""
        assert self._sdl is not None
        self._refresh_pads()
        lib = self._sdl.lib
        lib.SDL_UpdateGamepads()
        held: set[str] = set()
        active_pad = None
        for pad in self._pads.values():
            buttons = [name for name, index in SDL_BUTTONS.items() if lib.SDL_GetGamepadButton(pad, index)]
            pad_held = held_actions(buttons, lib.SDL_GetGamepadAxis(pad, SDL_AXIS_LEFTX),
                                    lib.SDL_GetGamepadAxis(pad, SDL_AXIS_LEFTY), self._held)
            if pad_held:
                active_pad = active_pad or pad
            held |= pad_held
        self._held = frozenset(held)
        return self._held, active_pad

    def _refresh_pads(self) -> None:
        assert self._sdl is not None
        current = self._sdl.gamepad_ids()
        for jid in current:
            if jid not in self._pads:
                pad = self._sdl.lib.SDL_OpenGamepad(jid)
                if pad:
                    self._pads[jid] = pad
        for jid in [j for j in self._pads if j not in current]:
            self._sdl.lib.SDL_CloseGamepad(self._pads.pop(jid))

    def _style(self, pad: int) -> str:
        assert self._sdl is not None
        return "playstation" if self._sdl.lib.SDL_GetGamepadType(pad) in PLAYSTATION_TYPES else "xbox"

