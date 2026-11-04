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
