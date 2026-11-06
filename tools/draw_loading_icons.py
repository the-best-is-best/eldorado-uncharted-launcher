# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""Draws El Dorado's own loading icons, one per game, into launcher/assets/loading/u1.png, u2.png, u3.png.

They stand for the objects the games turn while they load: a Spanish gold coin (Drake's Fortune), a phurba, the
Tibetan ritual dagger (Among Thieves), and a silver ring (Drake's Deception). Drawn here from shapes, nothing taken
from the games. The engine shows them on each game's window and taskbar button until it has taken the game's own
loading icon from the player's first loading screen (gow3_pc/gpu/shim/bbport_loading_icon.h).

Run: python tools/draw_loading_icons.py (Pillow).
"""
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 256
SCALE = 4  # drawn at 4x, then scaled down: smooth edges
OUT = Path(__file__).resolve().parent.parent / "launcher" / "assets" / "loading"


def canvas():
    return Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))


def finish(image):
    return image.resize((SIZE, SIZE), Image.LANCZOS)


def radial(size, inner, outer, centre=(0.38, 0.32)):
    """A square of size with a light from centre (fractions): inner colour there, outer at the far edge."""
    image = Image.new("RGBA", (size, size))
    px = image.load()
    cx, cy = centre[0] * size, centre[1] * size
    far = math.hypot(max(cx, size - cx), max(cy, size - cy))
    for y in range(size):
        for x in range(size):
            t = min(1.0, math.hypot(x - cx, y - cy) / far)
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * t) for i in range(3)) + (255,)
    return image


def masked(fill, mask):
    out = Image.new("RGBA", fill.size, (0, 0, 0, 0))
    out.paste(fill, (0, 0), mask)
    return out


def coin():
    s = SIZE * SCALE
    image = canvas()
    disc = Image.new("L", (s, s), 0)
    ImageDraw.Draw(disc).ellipse((s * 0.08, s * 0.08, s * 0.92, s * 0.92), fill=255)
    image.alpha_composite(masked(radial(s, (255, 226, 130), (150, 96, 22)), disc))
    d = ImageDraw.Draw(image)
    dark, deep = (120, 78, 18, 255), (92, 58, 12, 255)
    # Rim and a ring of beads.
    d.ellipse((s * 0.08, s * 0.08, s * 0.92, s * 0.92), outline=deep, width=int(s * 0.02))
    d.ellipse((s * 0.17, s * 0.17, s * 0.83, s * 0.83), outline=dark, width=int(s * 0.012))
    for i in range(36):
        a = i * math.tau / 36
        r, cx, cy, b = s * 0.375, s * 0.5, s * 0.5, s * 0.013
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        d.ellipse((x - b, y - b, x + b, y + b), fill=dark)
    # A quartered shield with a cross.
    x0, y0, x1, y1 = s * 0.33, s * 0.28, s * 0.67, s * 0.62
    shield = [(x0, y0), (x1, y0), (x1, y1 - s * 0.06), (s * 0.5, s * 0.74), (x0, y1 - s * 0.06)]
    d.polygon(shield, outline=deep, width=int(s * 0.016))
    d.line((s * 0.5, y0, s * 0.5, s * 0.72), fill=deep, width=int(s * 0.016))
    d.line((x0, s * 0.46, x1, s * 0.46), fill=deep, width=int(s * 0.016))
    for qx, qy in ((0.415, 0.37), (0.585, 0.55)):
        d.rectangle((s * (qx - 0.045), s * (qy - 0.045), s * (qx + 0.045), s * (qy + 0.045)), fill=dark)
    for qx, qy in ((0.585, 0.37), (0.415, 0.55)):
        for k in range(3):
            yy = s * (qy - 0.04 + k * 0.04)
            d.line((s * (qx - 0.05), yy, s * (qx + 0.05), yy), fill=dark, width=int(s * 0.01))
    # A highlight across the upper left.
    shine = Image.new("L", (s, s), 0)
    ImageDraw.Draw(shine).ellipse((s * 0.16, s * 0.12, s * 0.62, s * 0.5), fill=70)
    shine = ImageChops.multiply(shine.filter(ImageFilter.GaussianBlur(s * 0.05)), disc)
    image.alpha_composite(masked(Image.new("RGBA", (s, s), (255, 250, 220, 255)), shine))
    return finish(image)


def phurba():
    s = SIZE * SCALE
    image = canvas()
    d = ImageDraw.Draw(image)
    gold = radial(s, (255, 220, 120), (140, 92, 26), centre=(0.42, 0.3))
    cx = s * 0.5
    shapes = Image.new("L", (s, s), 0)
    m = ImageDraw.Draw(shapes)
    # Head (a knob with a small top), the handle's three bands, the guard.
    m.ellipse((cx - s * 0.075, s * 0.05, cx + s * 0.075, s * 0.19), fill=255)
    m.ellipse((cx - s * 0.03, s * 0.02, cx + s * 0.03, s * 0.08), fill=255)
    for top, half in ((0.19, 0.05), (0.27, 0.06), (0.35, 0.05)):
        m.rounded_rectangle((cx - s * half, s * top, cx + s * half, s * (top + 0.075)), radius=s * 0.02, fill=255)
    m.ellipse((cx - s * 0.11, s * 0.43, cx + s * 0.11, s * 0.5), fill=255)
    image.alpha_composite(masked(gold, shapes))
    # The three-sided blade: a long point, its middle edge lighter.
    blade_l = [(cx - s * 0.085, s * 0.49), (cx, s * 0.49), (cx, s * 0.97)]
    blade_r = [(cx, s * 0.49), (cx + s * 0.085, s * 0.49), (cx, s * 0.97)]
    d.polygon(blade_l, fill=(232, 200, 120, 255))
    d.polygon(blade_r, fill=(176, 136, 60, 255))
    d.line((cx, s * 0.5, cx, s * 0.95), fill=(255, 238, 180, 255), width=int(s * 0.01))
    # Lines between the parts and on the bands.
    line = (110, 70, 16, 255)
    for y in (0.19, 0.27, 0.345, 0.425, 0.49):
        d.line((cx - s * 0.06, s * y, cx + s * 0.06, s * y), fill=line, width=int(s * 0.012))
    for top in (0.205, 0.285, 0.365):
        for k in range(3):
            x = cx + s * (-0.03 + k * 0.03)
            d.line((x, s * top, x, s * (top + 0.045)), fill=line, width=int(s * 0.008))
    return finish(image)


def ring():
    s = SIZE * SCALE
    image = canvas()
    outer = (s * 0.14, s * 0.08, s * 0.86, s * 0.92)
    inner = (s * 0.32, s * 0.2, s * 0.74, s * 0.84)
    band = Image.new("L", (s, s), 0)
    m = ImageDraw.Draw(band)
    m.ellipse(outer, fill=255)
    m.ellipse(inner, fill=0)
    image.alpha_composite(masked(radial(s, (236, 236, 240), (92, 92, 104), centre=(0.3, 0.25)), band))
    d = ImageDraw.Draw(image)
    edge = (60, 60, 70, 255)
    d.ellipse(outer, outline=edge, width=int(s * 0.012))
    d.ellipse(inner, outline=edge, width=int(s * 0.012))
    # The inside of the far side, darker: the ring stands at an angle.
    shade = Image.new("L", (s, s), 0)
    ImageDraw.Draw(shade).ellipse((s * 0.32, s * 0.2, s * 0.84, s * 0.84), fill=110)
    shade = ImageChops.multiply(shade, band).filter(ImageFilter.GaussianBlur(s * 0.02))
    image.alpha_composite(masked(Image.new("RGBA", (s, s), (30, 30, 40, 255)), shade))
    # An engraved line of marks around the front.
    for i in range(14):
        a = math.radians(110 + i * 11)
        x = s * 0.5 + s * 0.3 * math.cos(a) - s * 0.04
        y = s * 0.5 + s * 0.38 * math.sin(a)
        d.line((x, y - s * 0.025, x, y + s * 0.025), fill=(80, 80, 92, 255), width=int(s * 0.01))
    return finish(image)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in (("u1", coin), ("u2", phurba), ("u3", ring)):
        draw().save(OUT / f"{name}.png")
        print(f"Wrote {OUT / (name + '.png')}")


if __name__ == "__main__":
    main()
