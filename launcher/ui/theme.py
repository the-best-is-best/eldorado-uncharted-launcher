# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The colors of qml/Theme.qml for the Python side (the drawn background): read from that one file, so a color
lives in one place. No Qt here; ui/background.py turns the values into QColor."""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

THEME_FILE = Path(__file__).resolve().parent / "qml" / "Theme.qml"
COLOR_LINE = re.compile(r'readonly\s+property\s+color\s+(\w+)\s*:\s*"(#[0-9a-fA-F]{6,8})"')


def read_colors(text: str) -> dict[str, str]:
    """Theme.qml's `readonly property color <name>: "#rrggbb"` lines, by name."""
    return {name: value for name, value in COLOR_LINE.findall(text)}


@cache
def colors(file: Path = THEME_FILE) -> dict[str, str]:
    return read_colors(file.read_text(encoding="utf-8"))


def color(name: str) -> str:
    """A theme color as "#rrggbb"; a name Theme.qml lacks is a KeyError (a bug, found at the first draw)."""
    return colors()[name]
