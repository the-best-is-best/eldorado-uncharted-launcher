# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""Icons: El Dorado's own (drawn here), and each game's, read from the player's own copy of the game.

The Collection's sce_sys/trophy holds one trophy pack per game (trophy01.trp Drake's Fortune,
trophy02.trp Among Thieves, trophy03.trp Drake's Deception), each with the game's icon (ICON0.PNG,
320x176 with transparency). The packages carry no picture from the game: the icons are made on
the player's PC, from their files, into analysis/uncharted-user/icons.

A TRP pack: a big-endian header (magic 0xDCA24D00, version, file size, file count at 16, entry
size at 20) and from 0x60 one entry per file: a 32-byte name, its offset and size (64-bit).
"""
import io
import math
import struct
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def trophy_icon(game_dir, number):
    """The game's icon (RGBA) from its trophy pack, or None."""
    path = Path(game_dir) / "sce_sys" / "trophy" / f"trophy0{number}.trp"
    try:
        with open(path, "rb") as pack:
            header = pack.read(0x60)
            if len(header) < 0x60 or struct.unpack_from(">I", header, 0)[0] != 0xDCA24D00:
                return None
            count, entry_size = struct.unpack_from(">II", header, 16)
            if not 0 < count < 4096 or not 40 <= entry_size <= 256:
                return None
            entries = pack.read(count * entry_size)
            for i in range(count):
                entry = entries[i * entry_size:(i + 1) * entry_size]
                name = entry[:32].split(b"\0")[0].decode("latin-1").upper()
                if name == "ICON0.PNG":
                    offset, size = struct.unpack_from(">QQ", entry, 32)
                    if not 0 < size < (8 << 20):
                        return None
                    pack.seek(offset)
                    return Image.open(io.BytesIO(pack.read(size))).convert("RGBA")
    except (OSError, ValueError, struct.error):
        return None
    return None


def square(image, size=256, fill=(0, 0, 0, 0)):
    """The picture centred on a square, as large as fits."""
    out = Image.new("RGBA", (size, size), fill)
    copy = image.copy()
    copy.thumbnail((size, size), Image.LANCZOS)
    out.alpha_composite(copy, ((size - copy.width) // 2, (size - copy.height) // 2))
    return out


def game_icon_file(game_dir, number, folder):
    """analysis/uncharted-user/icons/u<n>.ico (made once from the trophy pack), or None."""
    target = Path(folder) / f"u{number}.ico"
    source = Path(game_dir) / "sce_sys" / "trophy" / f"trophy0{number}.trp"
    try:
        if target.is_file() and source.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
            return target
    except OSError:
        pass
    icon = trophy_icon(game_dir, number)
    if icon is None:
        return None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        square(icon).save(target, sizes=ICO_SIZES)
        return target
    except OSError:
        return None


def eldorado_icon(size=256):
    """El Dorado's icon, after the series: an old gold coin like Drake's ring, "SIC PARVIS MAGNA" (the
    Drake family motto) engraved around a compass rose, on a scrap of an old map. All drawn here."""
    scale = 4  # drawn large, scaled down smooth
    s = size * scale
    c = s / 2
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # The map: aged parchment, darker at the edges, a few faint contour lines.
    paper = Image.new("RGBA", (s, s), (222, 200, 156, 255))
    edge = Image.new("L", (s, s), 0)
    ImageDraw.Draw(edge).rounded_rectangle((s * 0.06, s * 0.06, s * 0.94, s * 0.94), int(s * 0.2), fill=255)
    edge = ImageChops.invert(edge.filter(ImageFilter.GaussianBlur(s * 0.08)))
    paper = Image.composite(Image.new("RGBA", (s, s), (120, 84, 44, 255)), paper, edge)
    lines = ImageDraw.Draw(paper)
    for ring in range(1, 9):
        r = s * (0.18 + ring * 0.07)
        lines.arc((c - r * 1.15, c - r * 0.9, c + r * 1.15, c + r * 0.9), 200 + ring * 9, 330 + ring * 7,
                  fill=(150, 112, 66, 110), width=max(2, s // 260))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), int(s * 0.22), fill=255)
    image.paste(paper, (0, 0), mask)
    draw = ImageDraw.Draw(image)
    # The coin: a shadow, the rim, the face.
    rim, face = s * 0.43, s * 0.35
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((c - rim, c - rim + s * 0.025, c + rim, c + rim + s * 0.025), fill=(40, 24, 8, 170))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s * 0.02)))
    draw = ImageDraw.Draw(image)
    dark, gold, light, ink = (150, 104, 36, 255), (214, 164, 72, 255), (246, 212, 132, 255), (110, 72, 22, 255)
    draw.ellipse((c - rim, c - rim, c + rim, c + rim), fill=dark)
    draw.ellipse((c - rim * 0.97, c - rim * 0.97, c + rim * 0.97, c + rim * 0.97), fill=gold)
    shine = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(shine).ellipse((c - rim * 0.9, c - rim * 0.95, c + rim * 0.5, c + rim * 0.3), fill=(255, 236, 180, 90))
    image.alpha_composite(shine.filter(ImageFilter.GaussianBlur(s * 0.05)))
    draw = ImageDraw.Draw(image)
    draw.ellipse((c - face, c - face, c + face, c + face), outline=ink, width=max(3, s // 110))
    # The motto around the face.
    font = None
    for name in ("georgiab.ttf", "timesbd.ttf", "arialbd.ttf"):
        try:
            font = ImageFont.truetype(name, int(s * 0.062))
            break
        except OSError:
            continue
    if font is not None:
        text, radius = "SIC PARVIS MAGNA  •  SIC PARVIS MAGNA  •  ", (rim + face) / 2
        step = 360 / len(text)
        for i, letter in enumerate(text):
            angle = -90 + i * step
            glyph = Image.new("RGBA", (int(s * 0.1), int(s * 0.1)), (0, 0, 0, 0))
            ImageDraw.Draw(glyph).text((glyph.width / 2, glyph.height / 2), letter, font=font, fill=ink, anchor="mm")
            glyph = glyph.rotate(-angle - 90, resample=Image.BICUBIC)
            a = math.radians(angle)
            image.alpha_composite(glyph, (int(c + math.cos(a) * radius - glyph.width / 2),
                                          int(c + math.sin(a) * radius - glyph.height / 2)))
    draw = ImageDraw.Draw(image)

    def point(angle, length, width, colors):
        """A compass point: two halves, light and dark."""
        a = math.radians(angle)
        tip = (c + math.cos(a) * length, c + math.sin(a) * length)
        left = (c + math.cos(a + math.pi / 2) * width, c + math.sin(a + math.pi / 2) * width)
        right = (c + math.cos(a - math.pi / 2) * width, c + math.sin(a - math.pi / 2) * width)
        draw.polygon([(c, c), left, tip], fill=colors[0])
        draw.polygon([(c, c), tip, right], fill=colors[1])

    for angle in (45, 135, 225, 315):
        point(angle, face * 0.62, s * 0.04, (ink, dark))
    for angle in (270, 0, 90, 180):
        point(angle, face * 0.92, s * 0.06, (light, ink))
    r = s * 0.03
    draw.ellipse((c - r, c - r, c + r, c + r), fill=ink)
    return image.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    # Writes launcher/assets/eldorado.ico and eldorado.png.
    assets = Path(__file__).resolve().parent / "assets"
    icon = eldorado_icon(256)
    icon.save(assets / "eldorado.png")
    icon.save(assets / "eldorado.ico", sizes=ICO_SIZES)
    print(f"Wrote {assets / 'eldorado.ico'}")
