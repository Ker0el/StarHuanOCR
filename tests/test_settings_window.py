from app.config import Config
from app.ui.settings_window import SettingsWindow


def test_settings_defaults_to_config_hotkey(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(hotkey="F1"), "cpu")
    assert w.hotkey_edit.text() == "F1"


def test_settings_accepts_bare_letter_hotkey(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(hotkey="F1"), "cpu")
    w._apply_hotkey_text("Q")
    assert w.hotkey_edit.text() == "Q"


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


def test_device_label_explains_cpu_fallback():
    from app.ui.settings_window import device_label_text

    assert device_label_text("cuda", True) == "GPU · CUDA"
    assert device_label_text("dml", True) == "GPU · DirectML"
    assert device_label_text("cpu", True) == "CPU（当前运行库不带 GPU 支持）"
    assert device_label_text("cpu", False) == "CPU（设置里已关闭 GPU）"


def test_hotkey_edit_records_printscreen(qtbot):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    from app.ui.settings_window import HotkeyEdit

    edit = HotkeyEdit()
    qtbot.addWidget(edit)
    recorded = []
    edit.recorded.connect(recorded.append)
    edit.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Print, Qt.KeyboardModifier.NoModifier, "")
    )
    assert recorded == ["PrintScreen"]


def test_hotkey_edit_records_ctrl_space(qtbot):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    from app.ui.settings_window import HotkeyEdit

    edit = HotkeyEdit()
    qtbot.addWidget(edit)
    recorded = []
    edit.recorded.connect(recorded.append)
    edit.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier, " ")
    )
    assert recorded == ["Ctrl+Space"]


def test_settings_shows_author_link(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    assert "space.bilibili.com/177308205" in w.author_label.text()
    assert w.author_label.openExternalLinks() is True


def test_translation_details_hidden_until_enabled(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(), "cpu")
    assert w.translation_details.isHidden() is True
    w.translation_switch.setChecked(True)
    assert w.translation_details.isHidden() is False


def test_api_key_change_is_saved(qtbot, tmp_path, monkeypatch):
    from app.ui import settings_window as module

    saved = []
    monkeypatch.setattr(module, "save_config", lambda cfg, *a, **k: saved.append(cfg.deepseek_api_key))
    w = module.SettingsWindow()
    qtbot.addWidget(w)
    w.open(Config(translation_enabled=True), "cpu")
    w.api_key_edit.setText("sk-xyz")
    w.api_key_edit.editingFinished.emit()
    assert "sk-xyz" in saved


def test_settings_shows_reward_qr(qtbot):
    w = SettingsWindow()
    qtbot.addWidget(w)
    pixmap = w.reward_label.pixmap()
    assert pixmap is not None
    assert pixmap.isNull() is False
