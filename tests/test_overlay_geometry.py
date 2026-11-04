from PySide6.QtCore import QPoint, QRect

from app.overlay import normalize_selection


def test_normalize_reversed_drag():
    r = normalize_selection(QPoint(100, 80), QPoint(20, 10), QRect(0, 0, 500, 400))
    assert r == QRect(20, 10, 80, 70)


def test_normalize_clamps_to_bounds():
    r = normalize_selection(QPoint(-50, -50), QPoint(700, 700), QRect(0, 0, 500, 400))
    assert r == QRect(0, 0, 500, 400)


def test_tiny_selection_is_empty():
    assert normalize_selection(QPoint(10, 10), QPoint(13, 13), QRect(0, 0, 500, 400)).isEmpty()


def test_negative_origin_screen_preserves_global_coords():
    bounds = QRect(-1920, 0, 1920, 1080)
    r = normalize_selection(QPoint(-1900, 100), QPoint(-1000, 500), bounds)
    assert r == QRect(-1900, 100, 900, 400)


def test_full_screen_selection_is_accepted():
    r = normalize_selection(QPoint(0, 0), QPoint(500, 400), QRect(0, 0, 500, 400))
    assert r == QRect(0, 0, 500, 400)
