# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The home screen's background, served to QML as image://background/<key>?<version>: core/art.py's choice (a
save picture, the game's own art or its cover) cut and scaled to the screen without stretching, then darkened
toward the left and the bottom where the text and the cards sit. Without any picture, El Dorado's own map is
drawn here with QPainter. Qt calls requestImage on its image thread, so nothing here touches the window."""
from __future__ import annotations

import math
import random
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtQuick import QQuickImageProvider

from core import art
from ui import theme

# Theme.qml's leather, parchment and gold (the drawn map and the shade use them), read from that file.
LEATHER = QColor(theme.color("base"))
LEATHER_TOP = QColor(theme.color("baseTop"))
GOLD = QColor(theme.color("gold"))
PARCHMENT = QColor(theme.color("parchment"))
DEFAULT_SIZE = QSize(1280, 720)
# The shade: as dark as this at the left edge and at the bottom edge, fading out at these fractions of the size.
SHADE_LEFT, SHADE_LEFT_END = 165, 0.62
SHADE_BOTTOM, SHADE_BOTTOM_START = 205, 0.30
SHADE_EVERYWHERE = 30
# A bright picture (the Collection's parchment key art) is darkened more, up to this, so the text over it reads.
BRIGHT_FROM, BRIGHT_SHADE = 0.38, 130
# The cover's left part fades into the dark over this fraction of its width; its top and bottom edges a little.
COVER_FADE, COVER_EDGE = 0.6, 0.12
SMOOTH = Qt.TransformationMode.SmoothTransformation
STRETCH = Qt.AspectRatioMode.IgnoreAspectRatio


class BackgroundProvider(QQuickImageProvider):
    """choose(key) says which picture stands behind a game; the image is drawn at the size QML asks for."""

    def __init__(self, choose: Callable[[str], art.Picture]) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._choose = choose

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: A002, N803 (Qt's names)
        key = id.split("?", 1)[0]
        wanted = requestedSize if requestedSize.isValid() and not requestedSize.isEmpty() else DEFAULT_SIZE
        image = render(self._choose(key), wanted.width(), wanted.height(), key)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


def render(picture: art.Picture, width: int, height: int, key: str) -> QImage:
    image = QImage(max(1, width), max(1, height), QImage.Format.Format_RGB32)
    image.fill(LEATHER)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    source = load(picture)
    if source is None:
        draw_map(painter, image.width(), image.height(), key)
    elif picture.fills:
        draw_filling(painter, source, picture.region, image.width(), image.height())
    else:
        draw_cover(painter, source, picture.region, image.width(), image.height())
    shade(painter, image.width(), image.height(), brightness(image))
    painter.end()
    return image


def brightness(image: QImage, step: int = 24) -> float:
    """The mean lightness (0..1) of the right part of the picture, where the title and PLAY sit, from a sample
    of its pixels."""
    total, count = 0.0, 0
    for y in range(0, image.height(), step):
        for x in range(image.width() // 2, image.width(), step):
            total += image.pixelColor(x, y).lightnessF()
            count += 1
    return total / count if count else 0.0


def load(picture: art.Picture) -> QImage | None:
    if picture.path is None:
        return None
    image = QImage(str(picture.path))
    return None if image.isNull() else image


def _cut(source: QImage, part: art.Rect) -> QImage:
    return source.copy(QRect(part.x, part.y, part.width, part.height))


def draw_filling(painter: QPainter, source: QImage, region: art.Region, width: int, height: int) -> None:
    part = art.fill_rect(source.width(), source.height(), region, width, height)
    shown = _cut(source, part)
    if art.enlargement(part, width) > art.SOFTEN_ABOVE:
        shown = soften(shown)
    painter.drawImage(0, 0, shown.scaled(width, height, STRETCH, SMOOTH))


def soften(image: QImage) -> QImage:
    """An old small picture, enlarged a lot: drawn through a half-size copy, so it comes out soft, not blocky."""
    return image.scaled(max(1, image.width() // 2), max(1, image.height() // 2), STRETCH, SMOOTH)


def draw_cover(painter: QPainter, source: QImage, region: art.Region, width: int, height: int) -> None:
    """The cover as tall as the screen on the right, its left part fading into the dark."""
    part, place = art.cover_rects(source.width(), source.height(), region, width, height)
    shown = _cut(source, part).scaled(place.width, place.height, STRETCH, SMOOTH)
    faded = QImage(shown.size(), QImage.Format.Format_ARGB32_Premultiplied)
    faded.fill(Qt.GlobalColor.transparent)
    fader = QPainter(faded)
    fader.drawImage(0, 0, shown)
    fader.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    sideways = QLinearGradient(0, 0, shown.width(), 0)
    for stop in (0.0, 0.15, 0.3, 0.45, COVER_FADE):
        sideways.setColorAt(stop, _alpha(min(1.0, stop / COVER_FADE) ** 1.6))
    sideways.setColorAt(1.0, _alpha(1.0))
    fader.fillRect(faded.rect(), QBrush(sideways))
    edges = QLinearGradient(0, 0, 0, shown.height())
    edges.setColorAt(0.0, _alpha(0.0))
    edges.setColorAt(COVER_EDGE, _alpha(1.0))
    edges.setColorAt(1.0 - COVER_EDGE, _alpha(1.0))
    edges.setColorAt(1.0, _alpha(0.0))
    fader.fillRect(faded.rect(), QBrush(edges))
    fader.end()
    painter.drawImage(place.x, place.y, faded)


def _alpha(fraction: float) -> QColor:
    return QColor(0, 0, 0, round(255 * max(0.0, min(1.0, fraction))))


def _leather(alpha: float) -> QColor:
    return QColor(LEATHER.red(), LEATHER.green(), LEATHER.blue(), round(max(0.0, min(255.0, alpha))))


def shade(painter: QPainter, width: int, height: int, lightness: float = 0.0) -> None:
    """Dark toward the left and the bottom (the cards, the log and the hints sit there), a little everywhere
    (more over a bright picture), and a touch of sepia: a photograph in Drake's journal."""
    area = QRect(0, 0, width, height)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    bright = max(0.0, min(1.0, (lightness - BRIGHT_FROM) / (1 - BRIGHT_FROM)))
    painter.fillRect(area, _leather(SHADE_EVERYWHERE + BRIGHT_SHADE * bright))
    sideways = QLinearGradient(0, 0, width, 0)
    for stop in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, SHADE_LEFT_END):
        sideways.setColorAt(stop, _leather(SHADE_LEFT * max(0.0, 1 - stop / SHADE_LEFT_END) ** 1.3))
    sideways.setColorAt(1.0, _leather(0))
    painter.fillRect(area, QBrush(sideways))
    downwards = QLinearGradient(0, 0, 0, height)
    downwards.setColorAt(0.0, _leather(0))
    for stop in (SHADE_BOTTOM_START, 0.45, 0.6, 0.75, 0.9, 1.0):
        reach = (stop - SHADE_BOTTOM_START) / (1 - SHADE_BOTTOM_START)
        downwards.setColorAt(stop, _leather(SHADE_BOTTOM * max(0.0, reach) ** 1.25))
    painter.fillRect(area, QBrush(downwards))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(area, QColor(PARCHMENT.red(), PARCHMENT.green(), PARCHMENT.blue(), 56))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


def draw_map(painter: QPainter, width: int, height: int, seed: str) -> None:
    """El Dorado's own picture for a game without one: dark leather, a parchment glow on the right with the
    contour lines of a hill in gold, a dotted route up to an X, and a compass rose in the corner. The same for a
    game every time (drawn from its key), no file needed."""
    rng = random.Random(seed)
    area = QRectF(0, 0, width, height)
    leather = QLinearGradient(0, 0, 0, height)
    leather.setColorAt(0.0, LEATHER_TOP)
    leather.setColorAt(1.0, LEATHER)
    painter.fillRect(area, QBrush(leather))
    top_x, top_y = width * (0.66 + rng.random() * 0.12), height * (0.40 + rng.random() * 0.14)
    glow = QRadialGradient(QPointF(top_x, top_y), max(width, height) * 0.6)
    glow.setColorAt(0.0, QColor(PARCHMENT.red(), PARCHMENT.green(), PARCHMENT.blue(), 64))
    glow.setColorAt(0.55, QColor(PARCHMENT.red(), PARCHMENT.green(), PARCHMENT.blue(), 18))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.fillRect(area, QBrush(glow))
    _draw_contours(painter, width, height, top_x, top_y, rng)
    _draw_route(painter, width, height, top_x, top_y, rng)
    _draw_rose(painter, QPointF(width * 0.92, height * 0.14), min(width, height) * 0.055)


def _gold(alpha: int) -> QColor:
    return QColor(GOLD.red(), GOLD.green(), GOLD.blue(), alpha)


def _draw_contours(painter: QPainter, width: int, height: int, top_x: float, top_y: float,
                   rng: random.Random) -> None:
    turns = [rng.random() * math.tau for _ in range(3)]
    thin = QPen(_gold(30), max(1.0, width / 1000))
    bold = QPen(_gold(60), max(1.0, width / 500))
    step_out = max(width, height) / 30
    for ring in range(1, 23):
        radius = ring * step_out
        path = QPainterPath()
        for step in range(145):
            angle = step / 144 * math.tau
            # Each ring leans a little differently: a hill, not a target.
            swell = (1 + 0.14 * math.sin(2 * angle + turns[0] + ring * 0.08) + 0.08 * math.cos(5 * angle + turns[1])
                     + 0.04 * math.sin(11 * angle + turns[2] + ring * 0.25))
            point = QPointF(top_x + math.cos(angle) * radius * swell * 1.3,
                            top_y + math.sin(angle) * radius * swell * 0.8)
            if step == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        painter.setPen(bold if ring % 4 == 0 else thin)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


def _draw_route(painter: QPainter, width: int, height: int, top_x: float, top_y: float, rng: random.Random) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_gold(85))
    start_x, start_y = width * 0.1, height * 0.9
    bend = rng.random() * math.tau
    dot = max(1.5, width / 600)
    for step in range(0, 48, 2):
        t = step / 47
        x = start_x + (top_x - start_x) * t + math.sin(t * 6 + bend) * width * 0.035
        y = start_y + (top_y - start_y) * t + math.cos(t * 4 + bend) * height * 0.05
        painter.drawEllipse(QPointF(x, y), dot, dot)
    painter.setPen(QPen(_gold(150), max(2.0, width / 420)))
    arm = max(4.0, width / 95)
    painter.drawLine(QPointF(top_x - arm, top_y - arm), QPointF(top_x + arm, top_y + arm))
    painter.drawLine(QPointF(top_x - arm, top_y + arm), QPointF(top_x + arm, top_y - arm))


def _draw_rose(painter: QPainter, center: QPointF, size: float) -> None:
    """A compass rose: a ring and an eight-point star, light and dark halves as an engraving."""
    painter.setPen(QPen(_gold(70), max(1.0, size / 18)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(center, size, size)
    painter.setPen(Qt.PenStyle.NoPen)
    for point in range(8):
        angle = point * math.pi / 4 - math.pi / 2
        reach = size * (0.95 if point % 2 == 0 else 0.55)
        side = size * 0.16
        tip = QPointF(center.x() + math.cos(angle) * reach, center.y() + math.sin(angle) * reach)
        left = QPointF(center.x() + math.cos(angle - math.pi / 2) * side,
                       center.y() + math.sin(angle - math.pi / 2) * side)
        right = QPointF(center.x() + math.cos(angle + math.pi / 2) * side,
                        center.y() + math.sin(angle + math.pi / 2) * side)
        for corner, alpha in ((left, 95), (right, 45)):
            half = QPainterPath(center)
            half.lineTo(corner)
            half.lineTo(tip)
            half.closeSubpath()
            painter.fillPath(half, _gold(alpha))
