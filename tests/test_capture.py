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


def test_crop_does_not_alias_source_image(qapp):
    import gc

    from PySide6.QtGui import QColor

    img = QImage(64, 32, QImage.Format.Format_RGB32)
    img.fill(QColor(10, 20, 30))
    out = crop_to_numpy(img, QRect(0, 0, 64, 32))
    # reshape 后 OWNDATA 为 False，但 base 必须持有自己的缓冲区，不能是 Qt 的
    assert out.base is not None and out.base.flags["OWNDATA"] is True
    del img
    gc.collect()
    assert out.shape == (32, 64, 3)
    assert int(out[0, 0, 0]) == 10
    assert int(out[0, 0, 1]) == 20
    assert int(out[0, 0, 2]) == 30
