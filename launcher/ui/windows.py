# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Windows calls the launcher needs before Qt starts: one launcher at a time, and its taskbar identity."""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9


class SingleInstance:
    """Holds a named mutex for the launcher's whole life. A second start finds the mutex taken."""

    def __init__(self, name: str) -> None:
        self._handle = None
        self.first = True
        if sys.platform != "win32":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        self._handle = kernel32.CreateMutexW(None, False, f"Local\\{name}")
        self.first = ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def bring_to_front(title: str) -> bool:
    """Shows the open launcher's window (restored if minimized). False when no window has that title."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32")
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
    window = user32.FindWindowW(None, title)
    if not window:
        return False
    if user32.IsIconic(window):
        user32.ShowWindow(window, SW_RESTORE)
    # The process the player just started may hand the foreground to another window.
    user32.SetForegroundWindow(window)
    return True


GAME_TITLE_END = " — El Dorado"


def game_window_open() -> bool:
    """Whether a game's window is up: the engine titles it "<game> — El Dorado"."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32")
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(window, _param):
        if user32.IsWindowVisible(window):
            length = user32.GetWindowTextLengthW(window)
            if length:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(window, buffer, length + 1)
                if buffer.value.endswith(GAME_TITLE_END):
                    found.append(window)
                    return False
        return True

    user32.EnumWindows(visit, 0)
    return bool(found)


def set_app_id(app_id: str) -> None:
    """Groups the launcher under its own taskbar button (not pythonw.exe's)."""
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def process_age() -> float:
    """Seconds since this process was created (the cold start measure includes Python's own start)."""
    if sys.platform != "win32":
        return 0.0
    import time

    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel32.GetProcessTimes(kernel32.GetCurrentProcess(), ctypes.byref(created), ctypes.byref(exited),
                             ctypes.byref(kernel), ctypes.byref(user))
    # FILETIME: 100 ns steps since 1601; time.time(): seconds since 1970.
    ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
    return time.time() - (ticks / 1e7 - 11644473600)
