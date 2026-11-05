# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""El Dorado's own icons for the home screen: drawn here (no icon font, no picture files), in one
style: gold line work with square ends, a little wear, the expedition's things (a journal, an idol,
a photograph, a compass, a scroll). Drawn four times larger and scaled down for smooth edges.

    icon(name, size, color) -> RGBA PIL image
    names: saves, trophies, gallery, settings, update, logs, quit, and the PlayStation buttons
    cross, circle, square, triangle (their own colors).
"""
import math

from PIL import Image, ImageDraw

SCALE = 4
# The PlayStation buttons' colors, a little warmer to sit on leather.
PAD_COLORS = {"cross": (124, 178, 232), "circle": (236, 102, 96), "square": (226, 140, 196),
              "triangle": (82, 206, 168)}
# The key hint glyphs the hub uses for them.
PAD_GLYPHS = {"✕": "cross", "○": "circle", "□": "square", "△": "triangle"}


def _rgb(color):
    if isinstance(color, str):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(color[:3])


def icon(name, size, color=(222, 176, 88)):
    big = size * SCALE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    rgb = _rgb(PAD_COLORS.get(name, color))
    ink = rgb + (255,)
    w = max(SCALE * 2, int(big * 0.085))  # line width
    m = big * 0.14                         # margin
    s = big
    draw = DRAWERS.get(name)
    if draw:
        draw(d, s, m, w, ink, rgb)
    return image.resize((size, size), Image.LANCZOS)


# -- the rail -------------------------------------------------------------------------------

def _saves(d, s, m, w, ink, rgb):
    """The expedition journal: a closed book, its strap and a bookmark ribbon."""
    x1, y1, x2, y2 = m * 1.2, m, s - m * 1.1, s - m
    d.rectangle((x1, y1, x2, y2), outline=ink, width=w)
    d.line((x1 + w * 2.2, y1, x1 + w * 2.2, y2), fill=ink, width=w)            # spine
    d.line((x2 - w * 0.5, s * 0.46, x2 + m * 0.6, s * 0.46), fill=ink, width=w)  # strap
    rx = x2 - (x2 - x1) * 0.32
    d.polygon([(rx - w, y2 - w), (rx + w, y2 - w), (rx + w, y2 + m * 0.75), (rx, y2 + m * 0.45),
               (rx - w, y2 + m * 0.75)], fill=ink)                              # ribbon
    for f in (0.36, 0.5, 0.64):                                                 # lines on the cover
        d.line((x1 + w * 4, s * f, x2 - w * 2.6, s * f), fill=rgb + (150,), width=max(1, w // 2))


def _trophies(d, s, m, w, ink, rgb):
    """A trophy cup with handles on a stepped base."""
    cx = s / 2
    top, cup_bottom = m * 1.05, s * 0.58
    d.chord((cx - s * 0.27, top - s * 0.3, cx + s * 0.27, cup_bottom), 0, 180, fill=ink)
    d.rectangle((cx - s * 0.27, top, cx + s * 0.27, top + w), fill=ink)
    d.arc((cx - s * 0.42, top + s * 0.02, cx - s * 0.16, top + s * 0.3), 90, 270, fill=ink, width=w)
    d.arc((cx + s * 0.16, top + s * 0.02, cx + s * 0.42, top + s * 0.3), 270, 90, fill=ink, width=w)
    d.rectangle((cx - w * 0.7, cup_bottom - w, cx + w * 0.7, s * 0.74), fill=ink)
    d.rectangle((cx - s * 0.17, s * 0.74, cx + s * 0.17, s * 0.74 + w * 1.3), fill=ink)
    d.rectangle((cx - s * 0.24, s - m - w * 1.2, cx + s * 0.24, s - m), fill=ink)


def _gallery(d, s, m, w, ink, rgb):
    """A photograph: its frame, mountains and the sun."""
    x1, y1, x2, y2 = m, m * 1.4, s - m, s - m * 1.4
    d.rectangle((x1, y1, x2, y2), outline=ink, width=w)
    d.line([(x1 + w, y2 - w), (s * 0.38, s * 0.48), (s * 0.52, s * 0.6), (s * 0.66, s * 0.42), (x2 - w, y2 - w)],
           fill=ink, width=w, joint="curve")
    r = s * 0.07
    d.ellipse((s * 0.66 - r, s * 0.32 - r, s * 0.66 + r, s * 0.32 + r), fill=ink)


def _settings(d, s, m, w, ink, rgb):
    """A compass rose: the expedition's settings."""
    cx = cy = s / 2
    R = s / 2 - m
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=ink, width=w)
    for k in range(4):
        a = math.pi / 2 * k
        tip = (cx + math.cos(a) * R * 0.92, cy - math.sin(a) * R * 0.92)
        l = (cx + math.cos(a + math.pi / 2) * R * 0.2, cy - math.sin(a + math.pi / 2) * R * 0.2)
        r = (cx + math.cos(a - math.pi / 2) * R * 0.2, cy - math.sin(a - math.pi / 2) * R * 0.2)
        d.polygon([tip, l, (cx, cy), r], fill=ink if k % 2 == 0 else rgb + (170,))
    d.ellipse((cx - w * 0.8, cy - w * 0.8, cx + w * 0.8, cy + w * 0.8), fill=(0, 0, 0, 0), outline=ink)


def _update(d, s, m, w, ink, rgb):
    """An arrow down into a chest."""
    cx = s / 2
    d.line((cx, m, cx, s * 0.58), fill=ink, width=w)
    d.polygon([(cx - s * 0.2, s * 0.44), (cx + s * 0.2, s * 0.44), (cx, s * 0.66)], fill=ink)
    d.line([(m, s * 0.62), (m, s - m), (s - m, s - m), (s - m, s * 0.62)], fill=ink, width=w, joint="curve")


def _logs(d, s, m, w, ink, rgb):
    """A scroll: rolled ends and lines of writing."""
    x1, x2 = m * 1.3, s - m * 1.3
    r = s * 0.085
    d.rectangle((x1, m + r, x2, s - m - r), outline=ink, width=w)
    d.ellipse((x1 - r, m, x1 + r, m + 2 * r), outline=ink, width=w)
    d.ellipse((x2 - r, s - m - 2 * r, x2 + r, s - m), outline=ink, width=w)
    for f in (0.36, 0.48, 0.6):
        d.line((x1 + w * 2.5, s * f, x2 - w * 2.5, s * f), fill=ink, width=max(1, w * 2 // 3))


def _quit(d, s, m, w, ink, rgb):
    """The power sign."""
    cx = cy = s / 2 + s * 0.03
    R = s / 2 - m
    d.arc((cx - R, cy - R, cx + R, cy + R), -60, 240, fill=ink, width=w)
    d.line((s / 2, m * 0.7, s / 2, s * 0.5), fill=ink, width=w)


# -- PlayStation buttons (key hints) --------------------------------------------------------

def _cross(d, s, m, w, ink, rgb):
    k = m * 1.2
    d.line((k, k, s - k, s - k), fill=ink, width=int(w * 1.3))
    d.line((k, s - k, s - k, k), fill=ink, width=int(w * 1.3))


def _circle(d, s, m, w, ink, rgb):
    d.ellipse((m, m, s - m, s - m), outline=ink, width=int(w * 1.3))


def _square(d, s, m, w, ink, rgb):
    k = m * 1.2
    d.rectangle((k, k, s - k, s - k), outline=ink, width=int(w * 1.3))


def _triangle(d, s, m, w, ink, rgb):
    k = m * 0.9
    d.polygon([(s / 2, k), (s - k, s - k * 1.2), (k, s - k * 1.2)], outline=ink, width=int(w * 1.3))


DRAWERS = {"saves": _saves, "trophies": _trophies, "gallery": _gallery, "settings": _settings, "update": _update,
           "logs": _logs, "quit": _quit, "cross": _cross, "circle": _circle, "square": _square,
           "triangle": _triangle}
