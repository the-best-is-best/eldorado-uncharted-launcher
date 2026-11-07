# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The size a game draws at and, with upscaling, the size it is brought up to."""
from __future__ import annotations

ASPECT_WIDTHS = {"16:10": 16 / 10, "16:9": 16 / 9, "21:9": 64 / 27, "32:9": 32 / 9}
UPSCALE_SCALES = {"quality": 1.5, "balanced": 1.7, "performance": 2.0, "ultra": 3.0}
TEMPORAL_UPSCALERS = ("fsr3", "fsr4", "fsr411", "dlss")
# Ultrawide monitors' common sizes at 21:9.
WIDE_21_9 = {1080: 2560, 1440: 3440, 1600: 3840}


def upscaler(ini: dict[str, str]) -> str:
    """The upscaler a game's settings file holds: a temporal one, else FSR 1, else "off"."""
    if ini.get("upscaler") in TEMPORAL_UPSCALERS:
        return ini["upscaler"]
    return "fsr1" if ini.get("fsr1") == "1" else "off"


def at_aspect(resolution: str, aspect: str) -> str:
    """The resolution at an aspect ratio: widths in steps of 16 (Uncharted 3 asserts it), heights in steps of 4."""
    width, height = (int(value) for value in resolution.split("x"))
    if aspect not in ASPECT_WIDTHS or aspect == "16:9":
        return resolution
    if ASPECT_WIDTHS[aspect] < 16 / 9:
        height = int(round(width / ASPECT_WIDTHS[aspect] / 4)) * 4
    elif aspect == "21:9" and height in WIDE_21_9:
        width = WIDE_21_9[height]
    else:
        width = int(round(height * ASPECT_WIDTHS[aspect] / 16)) * 16
    return f"{width}x{height}"


def sizes(game: dict, ini: dict[str, str]) -> tuple[str, str | None]:
    """(render size, output size or None without upscaling)."""
    output = at_aspect(str(game.get("resolution", "1920x1080")), str(game.get("aspect", "16:9")))
    scale = UPSCALE_SCALES.get(str(game.get("upscale", "off")))
    if not scale or upscaler(ini) == "off":
        return output, None
    width, height = (int(value) for value in output.split("x"))
    render = f"{max(16, round(width / scale / 16) * 16)}x{max(4, round(height / scale / 4) * 4)}"
    return render, output
