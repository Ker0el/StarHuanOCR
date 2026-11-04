"""设置窗口：快捷键 / 行为 / 识别 / 通用。"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app import APP_NAME, APP_VERSION
from app.config import Config, save_config
from app.hotkey import parse_hotkey
from app.ui.theme import enable_acrylic
from app.winapi import set_autostart

from qfluentwidgets import SwitchButton

GROUP_STYLE = """
QFrame#group { background: rgba(255,255,255,8); border: 1px solid rgba(255,255,255,24);
               border-radius: 8px; }
QLabel { color: #e8e8e8; }
QLabel#hint { color: #9a9a9a; font-size: 11px; }
QLineEdit { background: rgba(0,0,0,90); color: #f2f2f2; border: 1px solid rgba(255,255,255,30);
            border-radius: 6px; padding: 4px 8px; }
QComboBox { background: rgba(0,0,0,90); color: #f2f2f2; border: 1px solid rgba(255,255,255,30);
            border-radius: 6px; padding: 3px 8px; }
QComboBox QAbstractItemView { background: #262626; color: #f2f2f2; }
"""


class HotkeyEdit(QLineEdit):
    """点入后按键即录制，非法组合回调交给父窗口处理。"""

    recorded = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        text = event.text().strip().upper()
        key = event.key()
        parts: list[str] = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")

        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            parts.append(f"F{key - Qt.Key.Key_F1 + 1}")
        elif text.isalnum() and len(text) == 1:
            parts.append(text)
        else:
            return

        self.recorded.emit("+".join(parts))


class SettingsWindow(QWidget):
    changed = Signal(object)
    hotkey_rejected = Signal(str)

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle(f"{APP_NAME} 设置")
        self.setStyleSheet(GROUP_STYLE)
        self.setMinimumWidth(460)
        self._config = Config()

        self.hotkey_edit = HotkeyEdit()
        self.hotkey_edit.recorded.connect(self._apply_hotkey_text)
        self.hotkey_hint = QLabel("最少一个修饰键，或 F1–F12")
        self.hotkey_hint.setObjectName("hint")

        self.auto_copy_switch = SwitchButton()
        self.show_result_switch = SwitchButton()
        self.prefer_gpu_switch = SwitchButton()
        self.autostart_switch = SwitchButton()
        self.update_switch = SwitchButton()

        self.precision_combo = QComboBox()
        self.precision_combo.addItem("自动", "auto")
        self.precision_combo.addItem("快速（small）", "fast")
        self.precision_combo.addItem("高精度（medium）", "high")

        self.device_label = QLabel("CPU")
        self.version_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.version_label.setObjectName("hint")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addWidget(self._group("快捷键", [("截图并识别", self.hotkey_edit), ("", self.hotkey_hint)]))
        root.addWidget(
            self._group(
                "行为",
                [
                    ("自动复制到剪贴板", self.auto_copy_switch),
                    ("识别后弹出结果窗口", self.show_result_switch),
                ],
            )
        )
        root.addWidget(
            self._group(
                "识别",
                [
                    ("优先使用 GPU", self.prefer_gpu_switch),
                    ("识别精度", self.precision_combo),
                    ("当前设备", self.device_label),
                ],
            )
        )
        root.addWidget(
            self._group(
                "通用",
                [
                    ("开机自启", self.autostart_switch),
                    ("检查更新", self.update_switch),
                    ("版本", self.version_label),
                ],
            )
        )
        root.addStretch(1)

        self.auto_copy_switch.checkedChanged.connect(lambda v: self._update(auto_copy=v))
        self.show_result_switch.checkedChanged.connect(lambda v: self._update(show_result=v))
        self.prefer_gpu_switch.checkedChanged.connect(lambda v: self._update(prefer_gpu=v))
        self.autostart_switch.checkedChanged.connect(self._on_autostart)
        self.update_switch.checkedChanged.connect(lambda v: self._update(check_updates=v))
        self.precision_combo.currentIndexChanged.connect(
            lambda _: self._update(precision=self.precision_combo.currentData())
        )

    # --- 对外 ---
    def open(self, settings: Config, device: str) -> None:
        # 拷贝一份再编辑，避免直接改动调用方持有的对象，改动通过 changed 信号回传
        self._config = replace(settings)
        self.hotkey_edit.setText(settings.hotkey)
        self.auto_copy_switch.setChecked(settings.auto_copy)
        self.show_result_switch.setChecked(settings.show_result)
        self.prefer_gpu_switch.setChecked(settings.prefer_gpu)
        self.autostart_switch.setChecked(settings.autostart)
        self.update_switch.setChecked(settings.check_updates)
        index = self.precision_combo.findData(settings.precision)
        self.precision_combo.setCurrentIndex(max(index, 0))
        self.device_label.setText(device.upper())
        self.show()
        self.raise_()
        self.activateWindow()

    def _apply_hotkey_text(self, text: str) -> None:
        try:
            parse_hotkey(text)
        except ValueError as exc:
            self.hotkey_rejected.emit(str(exc))
            return
        self.hotkey_edit.setText(text)
        self._update(hotkey=text)

    # --- 内部 ---
    def _group(self, title: str, rows: list[tuple[str, QWidget]]) -> QWidget:
        frame = QFrame()
        frame.setObjectName("group")
        layout = QFormLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        layout.addRow(heading)
        for label, widget in rows:
            if not label:
                layout.addRow(widget)
                continue
            row = QHBoxLayout()
            row.addWidget(widget, 1)
            layout.addRow(QLabel(label), row)
        return frame

    def _update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self._config, key, value)
        save_config(self._config)
        self.changed.emit(self._config)

    def _on_autostart(self, enabled: bool) -> None:
        set_autostart(enabled)
        self._update(autostart=enabled)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        enable_acrylic(self)
