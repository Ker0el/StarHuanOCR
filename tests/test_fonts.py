from app.ui.fonts import load_app_font


def test_app_font_loads_source_han_sans(qapp):
    family = load_app_font()
    assert family, "字体未加载"
    assert "Noto" in family or "思源" in family or "Source Han" in family
