from app.config import Config
from app.ui.settings_window import SettingsWindow


def test_settings_defaults_to_config_hotkey(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(hotkey="F1"), "cpu")
    assert w.hotkey_edit.text() == "F1"


def test_settings_rejects_bare_letter_hotkey(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(hotkey="F1"), "cpu")
    w._apply_hotkey_text("Q")
    assert w.hotkey_edit.text() == "F1"


def test_hotkey_edit_records_ctrl_letter_via_keycode(qtbot):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    from app.ui.settings_window import HotkeyEdit

    edit = HotkeyEdit()
    qtbot.addWidget(edit)
    recorded = []
    edit.recorded.connect(recorded.append)
    # 真实环境里 Ctrl+Q 的 text() 是 \x11，不是 'q'
    edit.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Q, Qt.KeyboardModifier.ControlModifier, "\x11")
    )
    assert recorded == ["Ctrl+Q"]


def test_open_does_not_write_autostart(qtbot, monkeypatch):
    from app.ui import settings_window as module

    calls = []
    monkeypatch.setattr(module, "set_autostart", lambda enabled: calls.append(enabled))
    w = module.SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(autostart=True), "cpu")
    assert calls == []
