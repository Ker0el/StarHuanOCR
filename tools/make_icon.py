"""生成 assets/icon.ico：深色圆角底 + 取景框 + 文字线。"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "icon.ico"
SIZE = 256


def draw() -> QImage:
    image = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#1c1c1e"))
    painter.drawRoundedRect(QRectF(8, 8, SIZE - 16, SIZE - 16), 52, 52)

    pen = QPen(QColor("#4cc2ff"), 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    arm = 46
    m = 62
    for (x, y, dx, dy) in [
        (m, m, 1, 1),
        (SIZE - m, m, -1, 1),
        (m, SIZE - m, 1, -1),
        (SIZE - m, SIZE - m, -1, -1),
    ]:
        painter.drawLine(x, y, x + dx * arm, y)
        painter.drawLine(x, y, x, y + dy * arm)

    painter.setPen(QPen(QColor(255, 255, 255, 190), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(96, 108, 160, 108)
    painter.drawLine(96, 140, 176, 140)
    painter.drawLine(96, 172, 132, 172)
    painter.end()
    return image


def main() -> int:
    app = QGuiApplication(sys.argv)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ok = draw().save(str(OUT), "ico")
    print(f"{OUT} saved={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
