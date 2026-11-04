"""托盘图标与菜单。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.ui.icon import load_icon

MENU_STYLE = """
QMenu { background: #262626; color: #f2f2f2; border: 1px solid rgba(255,255,255,30);
        border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: rgba(76,194,255,60); }
QMenu::separator { height: 1px; background: rgba(255,255,255,25); margin: 4px 8px; }
"""


class TrayIcon(QObject):
    capture_requested = Signal()
    settings_requested = Signal()
    update_requested = Signal()
    quit_requested = Signal()

    def __init__(self, hotkey_text: str = "F1", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(load_icon(), self)
        self._tray.setToolTip("星幻OCR")

        self._menu = QMenu()
        self._menu.setStyleSheet(MENU_STYLE)

        self._capture_action = QAction(self)
        self._settings_action = QAction("设置", self)
        self._update_action = QAction("检查更新", self)
        self._quit_action = QAction("退出", self)
        self._menu.addAction(self._capture_action)
        self._menu.addAction(self._settings_action)
        self._menu.addAction(self._update_action)
        self._menu.addSeparator()
        self._menu.addAction(self._quit_action)

        self._capture_action.triggered.connect(self.capture_requested)
        self._settings_action.triggered.connect(self.settings_requested)
        self._update_action.triggered.connect(self.update_requested)
        self._quit_action.triggered.connect(self.quit_requested)

        self._tray.setContextMenu(self._menu)
        self.set_hotkey_text(hotkey_text)
        self._tray.show()

    def set_hotkey_text(self, text: str) -> None:
        self._capture_action.setText(f"截图识别（{text}）")

    def notify(self, title: str, message: str, msecs: int = 4000) -> None:
        try:
            self._tray.showMessage(title, message, self._tray.icon(), msecs)
        except Exception:
            pass

    def hide(self) -> None:
        self._tray.hide()
