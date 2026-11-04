from pathlib import Path

import cv2
import pytest

from app.ocr.engine import DEFAULT_MODELS_DIR, OcrEngine

pytestmark = pytest.mark.slow

ASSET = Path(__file__).parent / "assets" / "ch_zh.png"


def test_recognizes_fixture_chinese():
    image = cv2.imread(str(ASSET))
    assert image is not None, "缺少测试图片"
    engine = OcrEngine(DEFAULT_MODELS_DIR, device="cpu", tier="small")
    result = engine.recognize(image)
    assert "正品" in result.text
    assert result.line_count >= 1
    assert 0 < result.elapsed_ms < 5000
