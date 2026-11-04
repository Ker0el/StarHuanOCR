import ctypes

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

from app.capture import crop_to_numpy, grab_virtual_desktop, virtual_desktop_rect


def test_virtual_rect_matches_win32_metrics(qapp):
    u = ctypes.windll.user32
    expected = QRect(u.GetSystemMetrics(76), u.GetSystemMetrics(77),
                     u.GetSystemMetrics(78), u.GetSystemMetrics(79))
    assert virtual_desktop_rect() == expected


def test_grab_size_matches_virtual_rect(qapp):
    assert grab_virtual_desktop().size() == virtual_desktop_rect().size()


def test_crop_returns_requested_size(qapp):
    img = QImage(200, 100, QImage.Format.Format_RGB32)
    out = crop_to_numpy(img, QRect(10, 10, 50, 20))
    assert out.shape[:2] == (20, 50)
