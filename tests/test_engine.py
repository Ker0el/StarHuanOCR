import pytest

from app.ocr.engine import OcrEngine, choose_device, choose_tier


def test_cuda_wins_when_available():
    assert choose_device(True, ["CUDAExecutionProvider", "CPUExecutionProvider"]) == "cuda"


def test_dml_when_no_cuda():
    assert choose_device(True, ["DmlExecutionProvider", "CPUExecutionProvider"]) == "dml"


def test_cpu_when_gpu_disabled():
    assert choose_device(False, ["CUDAExecutionProvider"]) == "cpu"


def test_cpu_when_nothing_available():
    assert choose_device(True, []) == "cpu"


def test_auto_tier_uses_medium_on_gpu():
    assert choose_tier("auto", "cuda") == "medium"
    assert choose_tier("auto", "cpu") == "small"


def test_explicit_tier_overrides():
    assert choose_tier("fast", "cuda") == "small"
    assert choose_tier("high", "cpu") == "medium"


def test_unknown_precision_falls_back_to_auto():
    assert choose_tier("nonsense", "cpu") == "small"


def test_engine_raises_clear_error_when_models_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        OcrEngine(tmp_path, device="cpu", tier="small")


def test_engine_disables_text_direction_classifier(qapp):
    """不做方向分类：关掉可避免运行时下载 cls 模型，也让离线包可识别。"""
    from app.ocr.engine import DEFAULT_MODELS_DIR

    engine = OcrEngine(DEFAULT_MODELS_DIR, device="cpu", tier="small")
    assert engine._engine.cfg["Global"]["use_cls"] is False
