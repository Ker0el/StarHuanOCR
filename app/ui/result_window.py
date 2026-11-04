"""结果窗口与识别中的等待胶囊。"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.icon import load_icon
from app.ui.theme import enable_acrylic

WINDOW_WIDTH = 560
WINDOW_HEIGHT = 240
GAP = 8
BACKGROUND = QColor(32, 32, 32, 235)
BORDER = QColor(255, 255, 255, 28)
ACCENT = QColor("#4cc2ff")
COPIED_HINT = "√ 已复制到剪贴板"
COPIED_COLOR = "#4ade80"


def _clamp_position(x: int, y: int, w: int, h: int, avail: QRect) -> tuple[int, int]:
    x = max(avail.left(), min(x, avail.right() - w))
    y = max(avail.top(), min(y, avail.bottom() - h))
    return x, y


class ResultWindow(QWidget):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("星幻OCR")
        self.setWindowIcon(load_icon())

        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setPlaceholderText("未识别到文字")
        self.text_edit.setStyleSheet(
            "QPlainTextEdit { background: rgba(0,0,0,90); color: #f2f2f2;"
            " border: 1px solid rgba(255,255,255,30); border-radius: 8px; padding: 8px; }"
        )

        self.copied_label = QLabel(COPIED_HINT)
        self.copied_label.setStyleSheet(f"color: {COPIED_COLOR}; font-size: 12px;")
        self.copied_label.setVisible(False)

        self.copy_button = QPushButton("复制")
        self.close_button = QPushButton("关闭")
        for btn in (self.copy_button, self.close_button):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,20); color: #f2f2f2;"
                " border: 1px solid rgba(255,255,255,30); border-radius: 6px;"
                " padding: 4px 14px; }"
                "QPushButton:hover { background: rgba(255,255,255,40); }"
            )
        self.copy_button.clicked.connect(self.copy_text)
        self.close_button.clicked.connect(self.close_window)

        buttons = QHBoxLayout()
        buttons.addWidget(self.copied_label)
        buttons.addStretch(1)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.close_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(self.text_edit, 1)
        root.addLayout(buttons)

    # --- 对外 ---
    def show_result(self, text: str, anchor: QRect, copied: bool = False) -> None:
        self.text_edit.setPlainText(text)
        self.copy_button.setText("复制")
        self.copied_label.setVisible(copied)
        self._place(anchor)
        self.show()
        self.raise_()
        self.activateWindow()
        self.text_edit.setFocus()

    def copy_text(self) -> None:
        QGuiApplication.clipboard().setText(self.text_edit.toPlainText())
        self.copy_button.setText("已复制")
        self.copied_label.setVisible(True)

    def close_window(self) -> None:
        self.hide()
        self.closed.emit()

    # --- 内部 ---
    def _place(self, anchor: QRect) -> None:
        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        width = min(WINDOW_WIDTH, max(320, anchor.width()))
        height = WINDOW_HEIGHT
        x = anchor.center().x() - width // 2
        y = anchor.bottom() + GAP
        if y + height > avail.bottom():
            y = anchor.top() - height - GAP
        x, y = _clamp_position(x, y, width, height, avail)
        self.setGeometry(x, y, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(BACKGROUND)
        painter.setPen(QPen(BORDER, 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        enable_acrylic(self)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close_window()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.copy_text()
            return
        super().keyPressEvent(event)


class LoadingChip(QWidget):
    """识别中的占位胶囊：不抢焦点、不吃鼠标。"""

    BARS = (0.6, 0.8, 0.4)

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.resize(180, 64)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._spin)

    def show_at(self, anchor: QRect) -> None:
        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = anchor.right() - self.width()
        y = anchor.bottom() + GAP
        if y + self.height() > avail.bottom():
            y = anchor.top() - self.height() - GAP
        x, y = _clamp_position(x, y, self.width(), self.height(), avail)
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start()

    def hide_chip(self) -> None:
        self._timer.stop()
        self.hide()

    def _spin(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(BACKGROUND)
        painter.setPen(QPen(BORDER, 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        painter.setPen(QPen(ACCENT, 2))
        painter.drawArc(QRectF(14, 22, 20, 20), self._angle * 16, 270 * 16)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 70))
        for index, ratio in enumerate(self.BARS):
            width = int(110 * ratio)
            painter.drawRoundedRect(QRectF(48, 16 + index * 12, width, 6), 3, 3)
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        enable_acrylic(self)
