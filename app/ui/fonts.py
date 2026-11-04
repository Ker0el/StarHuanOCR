"""应用字体：随包携带思源黑体（Noto Sans SC）。"""
from __future__ import annotations

from pathlib import Path

FONT_PATH = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NotoSansSC-VF.ttf"
FALLBACK_FAMILY = "Microsoft YaHei"


def load_app_font() -> str:
    """把字体注册进 Qt，返回可用字族名；失败时回落到系统字体。"""
    if not FONT_PATH.exists():
        return FALLBACK_FAMILY
    try:
        from PySide6.QtGui import QFontDatabase

        font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
        if font_id == -1:
            return FALLBACK_FAMILY
        families = QFontDatabase.applicationFontFamilies(font_id)
        return families[0] if families else FALLBACK_FAMILY
    except Exception:
        return FALLBACK_FAMILY
