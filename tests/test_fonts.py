from app.ui.fonts import load_app_font


def test_app_font_loads_source_han_sans(qapp):
    family = load_app_font()
    assert family, "字体未加载"
    assert "Noto" in family or "思源" in family or "Source Han" in family


def test_app_font_uses_medium_weight(qapp):
    from PySide6.QtGui import QFont

    from app.ui.fonts import app_font

    font = app_font()
    assert font.weight() == QFont.Weight.Medium
    assert "Noto" in font.family() or "思源" in font.family()
