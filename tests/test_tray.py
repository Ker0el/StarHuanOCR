from PySide6.QtWidgets import QSystemTrayIcon

from app.ui.tray import TrayIcon


def test_left_click_requests_capture(qtbot):
    tray = TrayIcon("F1")
    calls = []
    tray.capture_requested.connect(lambda: calls.append(1))
    tray._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert calls == [1]


def test_context_menu_click_does_not_capture(qtbot):
    tray = TrayIcon("F1")
    calls = []
    tray.capture_requested.connect(lambda: calls.append(1))
    tray._tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    assert calls == []
