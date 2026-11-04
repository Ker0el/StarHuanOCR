import pytest
from PySide6.QtCore import QObject, QRect, Signal
from PySide6.QtGui import QImage

from app.config import Config
from app.ocr.engine import OcrResult, OcrWorker
from app.overlay import OverlayController
from app.pipeline import Pipeline
from app.ui.result_window import LoadingChip, ResultWindow


class _StubTranslator(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.calls = []

    def translate_async(self, text, key):
        self.calls.append((text, key))


def make_pipeline(config=None, translator=None) -> Pipeline:
    worker = OcrWorker(lambda: None)
    overlay = OverlayController()
    overlay.desktop = QImage(200, 100, QImage.Format.Format_RGB32)
    overlay.desktop_rect = QRect(0, 0, 200, 100)
    pipe = Pipeline(config or Config(), worker, overlay, ResultWindow(), LoadingChip(),
                    translator=translator)
    return pipe


@pytest.mark.parametrize("text", ["", "   "])
def test_pipeline_ignores_blank_result(qtbot, text, monkeypatch):
    pipe = make_pipeline()
    copied = []
    monkeypatch.setattr(pipe, "_copy", lambda t: copied.append(t))
    pipe._on_result(OcrResult(text=text, elapsed_ms=10, device="cpu", line_count=0))
    assert copied == []


def test_chip_not_left_visible_when_result_is_fast(qtbot):
    pipe = make_pipeline()
    pipe._on_selection(QRect(10, 10, 100, 50))
    pipe._on_result(OcrResult(text="你好", elapsed_ms=20, device="cpu", line_count=1))
    qtbot.wait(250)
    assert pipe.chip.isVisible() is False


def test_trigger_capture_refused_when_worker_failed(qtbot, monkeypatch):
    pipe = make_pipeline()
    pipe.worker.mark_failed()
    started = []
    monkeypatch.setattr(pipe.overlay, "start", lambda: started.append(1))
    messages = []
    pipe.status_changed.connect(messages.append)
    pipe.trigger_capture()
    assert started == []
    assert messages


def test_translate_button_hidden_without_key(qtbot):
    pipe = make_pipeline(Config(translation_enabled=True, deepseek_api_key=""))
    pipe._on_result(OcrResult(text="你好", elapsed_ms=10, device="cpu", line_count=1))
    assert pipe.window.translate_button.isHidden() is True


def test_translate_button_shown_with_key(qtbot):
    pipe = make_pipeline(Config(translation_enabled=True, deepseek_api_key="sk-x"), _StubTranslator())
    pipe._on_result(OcrResult(text="你好", elapsed_ms=10, device="cpu", line_count=1))
    assert pipe.window.translate_button.isHidden() is False


def test_auto_translate_triggers_request(qtbot):
    translator = _StubTranslator()
    pipe = make_pipeline(Config(translation_enabled=True, deepseek_api_key="sk-x", auto_translate=True), translator)
    pipe._on_result(OcrResult(text="Hello", elapsed_ms=10, device="cpu", line_count=1))
    assert translator.calls and translator.calls[0][0] == "Hello"


def test_translation_result_goes_to_window(qtbot):
    translator = _StubTranslator()
    pipe = make_pipeline(Config(translation_enabled=True, deepseek_api_key="sk-x"), translator)
    pipe._on_result(OcrResult(text="Hello", elapsed_ms=10, device="cpu", line_count=1))
    pipe.window.translate_button.click()
    assert translator.calls
    translator.finished.emit("你好")
    assert pipe.window.translation_view.toPlainText() == "你好"
