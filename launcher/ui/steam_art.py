# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Each game's Steam library pictures in El Dorado's own look, nothing of the game's: the drawn map of the home
screen (background.draw_map) warmed by the game's color, the game's drawn icon (launcher/assets/loading) large on
it, and a title set in the launcher's fonts (UNCHARTED, the game's name, its place), as the home screen's card.

make(key, folder) writes folder/p.png (portrait 600x900), wide.png (920x430), hero.png (the banner, 1920x620) and
logo.png (the title over the banner, transparent); core/steam.py puts them in Steam's grid folder. QImage and
QPainter only: it runs on a worker thread."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QRadialGradient

from core import games, paths
from ui import theme
from ui.background import draw_map

TALL, WIDE, HERO = (600, 900), (920, 430), (1920, 620)
LOGO_WIDTH = 1280
ICONS = paths.LAUNCHER_DIR / "assets" / "loading"
GOLD = QColor(theme.color("gold"))
INK = QColor("#f1e8d6")  # the title: the parchment's light
# Theme.qml's titleFont and strongFont.
TITLE_FONT, STRONG_FONT = "Georgia", "Segoe UI Semibold"


def accent(key: str) -> QColor:
    return QColor(theme.color(f"accent{key.upper()}"))


def _icon(key: str) -> QImage:
    image = QImage(str(ICONS / f"{key}.png"))
    if image.isNull():
        return image
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    # Without its empty edge.
    left, top, right, bottom = image.width(), image.height(), -1, -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 8:
                left, top, right, bottom = min(left, x), min(top, y), max(right, x), max(bottom, y)
    return image.copy(left, top, right - left + 1, bottom - top + 1) if right >= left else image


def _ground(painter: QPainter, size: tuple[int, int], key: str, glow_at: QPointF, glow_size: float,
            shade_left: float = 0.0) -> None:
    """The drawn map, the game's color glowing where its icon stands, and (shade_left) a darker left for text."""
    width, height = size
    draw_map(painter, width, height, key)
    color = accent(key)
    glow = QRadialGradient(glow_at, glow_size)
    glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 70))
    glow.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), 22))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.fillRect(QRectF(0, 0, width, height), glow)
    if shade_left > 0:
        shade = QLinearGradient(0, 0, width * shade_left, 0)
        shade.setColorAt(0.0, QColor(0, 0, 0, 150))
        shade.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(QRectF(0, 0, width * shade_left, height), shade)


def _draw_icon(painter: QPainter, icon: QImage, center: QPointF, height: float) -> None:
    if icon.isNull():
        return
    width = icon.width() * height / icon.height()
    # A soft dark shadow under it, then the icon.
    shadow = QRadialGradient(QPointF(center.x(), center.y() + height * 0.08), height * 0.62)
    shadow.setColorAt(0.0, QColor(0, 0, 0, 110))
    shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.fillRect(QRectF(center.x() - height, center.y() - height, height * 2, height * 2), shadow)
    painter.drawImage(QRectF(center.x() - width / 2, center.y() - height / 2, width, height), icon)


def _font(family: str, pixels: float, spacing: float = 0.0, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(1, round(pixels)))
    font.setWeight(weight)
    if spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


def _title_block(painter: QPainter, key: str, box: QRectF, scale: float, align: Qt.AlignmentFlag) -> None:
    """UNCHARTED (and the game's number), its name, its place: the home screen card's lines, fitted to `box`."""
    game = games.by_key(key)
    color = accent(key)
    top = "UNCHARTED" if game.number == "1" else f"UNCHARTED {game.number}"
    lines = [
        (top, _font(STRONG_FONT, 30 * scale, 9 * scale, QFont.Weight.DemiBold), GOLD),
        (game.title, _font(TITLE_FONT, 74 * scale), INK),
        (game.place, _font(STRONG_FONT, 22 * scale, 7 * scale, QFont.Weight.DemiBold), color),
    ]
    # The name shrinks to fit the box's width (DRAKE'S DECEPTION is long).
    name_font = lines[1][1]
    while QFontMetricsF(name_font).horizontalAdvance(game.title) > box.width() and name_font.pixelSize() > 10:
        name_font.setPixelSize(name_font.pixelSize() - 2)
    heights = [QFontMetricsF(font).height() for _, font, _ in lines]
    gaps = [10 * scale, 8 * scale]
    total = sum(heights) + sum(gaps) + 6 * scale  # with the rule under the name
    y = box.top() + (box.height() - total) / 2
    for index, (text, font, ink) in enumerate(lines):
        painter.setFont(font)
        painter.setPen(ink)
        painter.drawText(QRectF(box.left(), y, box.width(), heights[index]), int(align | Qt.AlignmentFlag.AlignVCenter),
                         text)
        y += heights[index]
        if index == 1:
            # A short rule in the game's color under the name, as the launcher's card.
            rule = 90 * scale
            x = box.left() if align == Qt.AlignmentFlag.AlignLeft else box.center().x() - rule / 2
            painter.fillRect(QRectF(x, y + 3 * scale, rule, 3 * scale), color)
            y += 6 * scale
        if index < len(gaps):
            y += gaps[index]


def _new(size: tuple[int, int], transparent: bool = False) -> QImage:
    image = QImage(size[0], size[1], QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0) if transparent else QColor(theme.color("base")))
    return image


def _painter(image: QImage) -> QPainter:
    painter = QPainter(image)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
                           | QPainter.RenderHint.TextAntialiasing)
    return painter


def make(key: str, folder: Path) -> Path:
    """The four pictures of one game into `folder`; returns the folder."""
    folder.mkdir(parents=True, exist_ok=True)
    icon = _icon(key)

    tall = _new(TALL)
    painter = _painter(tall)
    _ground(painter, TALL, key, QPointF(300, 330), 420)
    _draw_icon(painter, icon, QPointF(300, 330), 380)
    _title_block(painter, key, QRectF(30, 560, 540, 300), 0.82, Qt.AlignmentFlag.AlignHCenter)
    painter.end()

    wide = _new(WIDE)
    painter = _painter(wide)
    _ground(painter, WIDE, key, QPointF(220, 215), 320)
    _draw_icon(painter, icon, QPointF(220, 215), 320)
    _title_block(painter, key, QRectF(420, 40, 470, 350), 0.78, Qt.AlignmentFlag.AlignLeft)
    painter.end()

    hero = _new(HERO)
    painter = _painter(hero)
    _ground(painter, HERO, key, QPointF(1460, 310), 620, shade_left=0.45)
    _draw_icon(painter, icon, QPointF(1460, 310), 420)
    painter.end()

    logo = _new((LOGO_WIDTH, 420), transparent=True)
    painter = _painter(logo)
    _title_block(painter, key, QRectF(0, 0, LOGO_WIDTH, 420), 1.9, Qt.AlignmentFlag.AlignLeft)
    painter.end()

    for name, image in (("p", tall), ("wide", wide), ("hero", hero), ("logo", logo)):
        work = folder / f"{name}.png.tmp"
        image.save(str(work), "PNG")
        work.replace(folder / f"{name}.png")
    return folder
