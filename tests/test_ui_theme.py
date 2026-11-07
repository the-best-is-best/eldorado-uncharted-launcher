# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from ui import theme  # noqa: E402


def test_colors_are_read_from_theme_qml() -> None:
    found = theme.read_colors('    readonly property color base: "#140e09"\n'
                              '    readonly property color gold: "#deb058"   // a comment\n'
                              '    readonly property string titleFont: "Georgia"\n')
    assert found == {"base": "#140e09", "gold": "#deb058"}


def test_the_background_colors_are_in_theme_qml() -> None:
    for name in ("base", "baseTop", "gold", "parchment"):
        assert theme.color(name).startswith("#")
