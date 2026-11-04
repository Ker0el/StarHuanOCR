"""全屏蒙层与框选。"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.capture import grab_virtual_desktop, virtual_desktop_rect

MIN_SELECTION = 5
DIM_COLOR = QColor(0, 0, 0, 130)
BORDER_COLOR = QColor("#4cc2ff")
LABEL_BG = QColor(0, 0, 0, 170)


def normalize_selection(start: QPoint, end: QPoint, bounds: QRect) -> QRect:
    """把拖拽的起止点整理成与 bounds 求交的矩形；小于 5px 视为空。"""
    left, top = min(start.x(), end.x()), min(start.y(), end.y())
    width, height = abs(end.x() - start.x()), abs(end.y() - start.y())
    rect = QRect(left, top, width, height).intersected(bounds)
    if rect.width() < MIN_SELECTION or rect.height() < MIN_SELECTION:
        return QRect()
    return rect


class SelectionOverlay(QWidget):
    selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, image: QImage, geometry: QRect) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(geometry)
        self._bg = image
        self._origin: QPoint | None = None
        self._current: QPoint | None = None

    def begin(self, image: QImage, geometry: QRect) -> None:
        self._bg = image
        self.setGeometry(geometry)
        self.show()
        self.raise_()
        self.activateWindow()

    # --- 事件 ---
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        local = normalize_selection(self._origin, event.position().toPoint(), self.rect())
        self._origin = None
        self._current = None
        if local.isEmpty():
            self.cancelled.emit()
        else:
            self.selected.emit(local.translated(self.geometry().topLeft()))

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.cancelled.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()

    # --- 绘制 ---
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawImage(0, 0, self._bg)
        painter.fillRect(self.rect(), DIM_COLOR)

        if self._origin is None or self._current is None:
            painter.end()
            return

        local = normalize_selection(self._origin, self._current, self.rect())
        if local.isEmpty():
            painter.end()
            return

        painter.drawImage(local, self._bg, local)
        painter.setPen(QPen(BORDER_COLOR, 1))
        painter.drawRect(local.adjusted(0, 0, -1, -1))
        painter.setPen(QPen(BORDER_COLOR, 1, Qt.PenStyle.DashLine))
        painter.drawRect(local.adjusted(2, 2, -3, -3))

        label = f"{local.width()} × {local.height()}"
        metrics = painter.fontMetrics()
        box = metrics.boundingRect(label).adjusted(-6, -3, 6, 3)
        anchor = QRect(local.left(), local.top() - box.height() - 4, box.width(), box.height())
        if anchor.top() < 0:
            anchor.moveTop(local.top() + 4)
        painter.fillRect(anchor, LABEL_BG)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(anchor, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()


class OverlayController(QObject):
    selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overlays: list[SelectionOverlay] = []
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        desktop = grab_virtual_desktop()
        rect = virtual_desktop_rect()
        self._active = True

        for screen in QGuiApplication.screens():
            geo = screen.geometry()
            sub = desktop.copy(
                QRect(geo.x() - rect.x(), geo.y() - rect.y(), geo.width(), geo.height())
            )
            overlay = SelectionOverlay(sub, geo)
            overlay.selected.connect(self._on_selected)
            overlay.cancelled.connect(self._on_cancelled)
            overlay.show()
            overlay.raise_()
            overlay.activateWindow()
            self._overlays.append(overlay)

    def _close_all(self) -> None:
        overlays, self._overlays = self._overlays, []
        self._active = False
        for overlay in overlays:
            overlay.hide()
            overlay.close()

    def _on_selected(self, rect: QRect) -> None:
        if not self._active:
            return
        self._close_all()
        self.selected.emit(rect)

    def _on_cancelled(self) -> None:
        if not self._active:
            return
        self._close_all()
        self.cancelled.emit()
