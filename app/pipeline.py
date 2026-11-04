"""主流程：热键 → 框选 → 识别 → 复制 / 弹窗。"""
from __future__ import annotations

from PySide6.QtCore import QObject, QRect, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from app.capture import crop_to_numpy
from app.config import Config
from app.ocr.engine import OcrResult
from app.overlay import OverlayController

CHIP_DELAY_MS = 150


class Pipeline(QObject):
    status_changed = Signal(str)

    def __init__(self, config, worker, overlay: OverlayController, window, chip, tray=None) -> None:
        super().__init__()
        self.config: Config = config
        self.worker = worker
        self.overlay = overlay
        self.window = window
        self.chip = chip
        self.tray = tray
        self._anchor = QRect()
        self._chip_timer: QTimer | None = None

        overlay.selected.connect(self._on_selection)
        overlay.cancelled.connect(self._on_cancel)
        worker.finished.connect(self._on_result)
        worker.failed.connect(self._on_error)

    def replace_worker(self, worker) -> None:
        """换引擎（精度/GPU 开关变化）时重建工作线程。"""
        if self.worker is not None:
            try:
                self.worker.finished.disconnect(self._on_result)
                self.worker.failed.disconnect(self._on_error)
            except (RuntimeError, TypeError):
                pass
            self.worker.stop()
        self.worker = worker
        worker.finished.connect(self._on_result)
        worker.failed.connect(self._on_error)
        worker.start()

    # --- 触发 ---
    def trigger_capture(self) -> None:
        if getattr(self.worker, "is_failed", False):
            self.status_changed.emit("OCR 引擎不可用，无法截图识别。请检查 models 目录后重启程序。")
            return
        if self.overlay.is_active:
            return
        self.window.hide()
        self.chip.hide_chip()
        self.overlay.start()

    # --- 框选完成 ---
    def _on_selection(self, rect: QRect) -> None:
        desktop = self.overlay.desktop
        if desktop is None:
            return
        local = rect.translated(-self.overlay.desktop_rect.topLeft())
        image = crop_to_numpy(desktop, local)
        if image.size == 0:
            return
        self._begin_ocr(image, rect)

    def _begin_ocr(self, image, rect: QRect) -> None:
        if getattr(self.worker, "is_failed", False):
            self.status_changed.emit("OCR 引擎不可用。")
            return
        self._anchor = QRect(rect)
        self.window.hide()
        if self._chip_timer is not None:
            self._chip_timer.stop()
        self._chip_timer = QTimer(self)
        self._chip_timer.setSingleShot(True)
        self._chip_timer.timeout.connect(lambda: self.chip.show_at(self._anchor))
        self._chip_timer.start(CHIP_DELAY_MS)
        self.worker.submit(image)

    # --- 结果 ---
    def _on_result(self, result: OcrResult) -> None:
        self._stop_chip()
        text = result.text.strip()
        if not text:
            if self.config.show_result:
                self.window.show_result("", self._anchor)
            self.status_changed.emit("未识别到文字")
            return
        if self.config.auto_copy:
            self._copy(text)
        if self.config.show_result:
            self.window.show_result(text, self._anchor)
        self.status_changed.emit(f"识别完成 · {result.elapsed_ms} ms · {result.device}")

    def _on_error(self, message: str) -> None:
        self._stop_chip()
        self.status_changed.emit(message)
        if self.tray is not None:
            self.tray.notify("星幻OCR", message)

    def _on_cancel(self) -> None:
        self._stop_chip()

    def _stop_chip(self) -> None:
        if self._chip_timer is not None:
            self._chip_timer.stop()
            self._chip_timer = None
        self.chip.hide_chip()

    def _copy(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)
