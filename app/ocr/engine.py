"""OCR 引擎封装：设备探测、模型档位、单线程工作队列。"""
from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from app.ocr.layout import boxes_to_text

DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"

MODEL_FILES: dict[str, tuple[str, str]] = {
    "small": ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"),
    "medium": ("PP-OCRv6_det_medium.onnx", "PP-OCRv6_rec_medium.onnx"),
}

CPU_THREADS = 4
DET_LIMIT_SIDE_LEN = 960


@dataclass
class OcrResult:
    text: str
    elapsed_ms: int
    device: str
    line_count: int


def choose_device(prefer_gpu: bool, available: Sequence[str]) -> str:
    """CUDA > DirectML > CPU。"""
    if not prefer_gpu:
        return "cpu"
    if "CUDAExecutionProvider" in available:
        return "cuda"
    if "DmlExecutionProvider" in available:
        return "dml"
    return "cpu"


def choose_tier(precision: str, device: str) -> str:
    """auto 在 GPU 上用 medium、CPU 上用 small；显式档位优先。"""
    if precision in ("fast", "small"):
        return "small"
    if precision in ("high", "medium"):
        return "medium"
    return "small" if device == "cpu" else "medium"


def available_providers() -> list[str]:
    try:
        import onnxruntime as ort

        return list(ort.get_available_providers())
    except Exception:
        return []


class OcrEngine:
    def __init__(
        self,
        models_dir: Path = DEFAULT_MODELS_DIR,
        device: str = "cpu",
        tier: str = "small",
    ) -> None:
        det_name, rec_name = MODEL_FILES[tier]
        det_path = Path(models_dir) / det_name
        rec_path = Path(models_dir) / rec_name
        missing = [str(p) for p in (det_path, rec_path) if not p.exists()]
        if missing:
            raise FileNotFoundError("缺少 OCR 模型文件: " + ", ".join(missing))

        from rapidocr import EngineType, RapidOCR

        self.device = device
        self.tier = tier
        params = {
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.model_path": str(det_path),
            "Det.limit_type": "max",
            "Det.limit_side_len": DET_LIMIT_SIDE_LEN,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.model_path": str(rec_path),
            "Global.log_level": "error",
            # 截图场景不需要 180° 方向分类；关掉可避免运行时下载 cls 模型，
            # 否则离线包里每次识别都会因缺 cls 模型而失败。
            "Global.use_cls": False,
            "EngineConfig.onnxruntime.intra_op_num_threads": CPU_THREADS,
            "EngineConfig.onnxruntime.use_cuda": device == "cuda",
            "EngineConfig.onnxruntime.use_dml": device == "dml",
        }
        self._engine = RapidOCR(params=params)

    def warmup(self) -> None:
        blank = np.full((32, 32, 3), 255, dtype=np.uint8)
        try:
            self._engine(blank)
        except Exception:
            pass

    def recognize(self, image: np.ndarray) -> OcrResult:
        start = time.perf_counter()
        raw = self._engine(image)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        boxes = getattr(raw, "boxes", None)
        txts = getattr(raw, "txts", None)
        scores = getattr(raw, "scores", None)
        boxes = [] if boxes is None else boxes
        txts = () if txts is None else txts
        scores = () if scores is None else scores

        items = [
            (box, txt, float(scores[i]) if i < len(scores) else 1.0)
            for i, (box, txt) in enumerate(zip(boxes, txts))
        ]
        return OcrResult(
            text=boxes_to_text(items),
            elapsed_ms=elapsed_ms,
            device=self.device,
            line_count=len(txts),
        )


class _OcrThread(QThread):
    result_ready = Signal(object)
    error = Signal(str)
    ready = Signal()

    def __init__(self, factory: Callable[[], OcrEngine]) -> None:
        super().__init__()
        self._factory = factory
        self._queue: queue.Queue = queue.Queue()
        self.label = ""

    def submit(self, image: np.ndarray) -> None:
        self._queue.put(image)

    def stop(self) -> None:
        self._queue.put(None)

    def run(self) -> None:  # noqa: D102
        try:
            engine = self._factory()
            engine.warmup()
            self.label = f"{engine.device}/{engine.tier}"
            self.ready.emit()
        except Exception as exc:  # 引擎初始化失败必须让上层看见
            self.error.emit(f"OCR 引擎不可用：{exc}")
            return

        while True:
            image = self._queue.get()
            if image is None:
                return
            try:
                self.result_ready.emit(engine.recognize(image))
            except Exception as exc:
                self.error.emit(f"识别失败：{exc}")


class OcrWorker(QObject):
    """单工作线程 + 串行队列；ONNX Runtime 会话非线程安全。"""

    finished = Signal(object)
    failed = Signal(str)
    ready = Signal(str)

    def __init__(self, factory: Callable[[], OcrEngine], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread = _OcrThread(factory)
        self._thread.result_ready.connect(self.finished)
        self._thread.error.connect(self._on_error)
        self._thread.ready.connect(self._on_ready)
        self._failed = False
        self._ready = False

    @property
    def is_failed(self) -> bool:
        return self._failed

    @property
    def is_ready(self) -> bool:
        return self._ready

    def mark_failed(self) -> None:
        """外部（或测试）标记引擎不可用，避免继续往死线程投递。"""
        self._failed = True
        self._ready = False

    def _on_error(self, message: str) -> None:
        self.mark_failed()
        self.failed.emit(message)

    def _on_ready(self) -> None:
        self._ready = True
        self.ready.emit(self._thread.label)

    def start(self) -> None:
        self._thread.start()

    def submit(self, image: np.ndarray) -> None:
        if self._failed:
            return
        self._thread.submit(image)

    def stop(self) -> None:
        self._thread.stop()
        self._thread.wait(3000)
