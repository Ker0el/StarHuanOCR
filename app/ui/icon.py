"""应用图标：黑底 + 蓝色科技感星形。"""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
    QRadialGradient,
)

ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"

BG_TOP = QColor("#0b1020")
BG_BOTTOM = QColor("#05070d")
STAR_CORE = QColor("#8ee6ff")
STAR_EDGE = QColor("#1d4ed8")
GLOW = QColor(76, 194, 255, 60)


def star_path(cx: float, cy: float, outer: float, inner: float, points: int = 5) -> QPainterPath:
    path = QPainterPath()
    step = math.pi / points
    angle = -math.pi / 2
    for index in range(points * 2):
        radius = outer if index % 2 == 0 else inner
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius
        if index == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
        angle += step
    path.closeSubpath()
    return path


def draw_icon(size: int = 256) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = size / 256.0

    # 深色圆角底板
    background = QLinearGradient(0, 0, 0, size)
    background.setColorAt(0.0, BG_TOP)
    background.setColorAt(1.0, BG_BOTTOM)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(6 * scale, 6 * scale, size - 12 * scale, size - 12 * scale), 54 * scale, 54 * scale)

    cx = cy = size / 2

    # 外发光：几层递减透明度的星形
    for radius, alpha in ((108, 18), (92, 26), (78, 34)):
        glow = QColor(GLOW)
        glow.setAlpha(alpha)
        painter.setBrush(glow)
        painter.drawPath(star_path(cx, cy, radius * scale, radius * 0.42 * scale))

    # 星体：中心亮青到边缘深蓝
    body = QRadialGradient(QPointF(cx, cy - 14 * scale), 96 * scale)
    body.setColorAt(0.0, STAR_CORE)
    body.setColorAt(0.45, QColor("#3fa8ff"))
    body.setColorAt(1.0, STAR_EDGE)
    painter.setBrush(body)
    star = star_path(cx, cy, 84 * scale, 34 * scale)
    painter.drawPath(star)

    # 高光细边
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QColor(180, 235, 255, 150))
    painter.drawPath(star_path(cx, cy, 84 * scale, 34 * scale))

    # 科技感角标
    painter.setPen(QColor(76, 194, 255, 170))
    arm = 22 * scale
    margin = 34 * scale
    for (x, y, dx, dy) in [
        (margin, margin, 1, 1),
        (size - margin, margin, -1, 1),
        (margin, size - margin, 1, -1),
        (size - margin, size - margin, -1, -1),
    ]:
        painter.drawLine(QPointF(x, y), QPointF(x + dx * arm, y))
        painter.drawLine(QPointF(x, y), QPointF(x, y + dy * arm))

    painter.end()
    return pixmap


def fallback_icon() -> QIcon:
    return QIcon(draw_icon(64))


def load_icon() -> QIcon:
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))
    return fallback_icon()
