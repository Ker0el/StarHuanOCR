import numpy as np

from app.ocr.engine import OcrWorker


def test_worker_marks_failed_and_stays_dead(qtbot):
    def boom():
        raise FileNotFoundError("缺少模型")

    worker = OcrWorker(boom)
    errors = []
    worker.failed.connect(errors.append)
    worker.start()
    qtbot.waitUntil(lambda: bool(errors), timeout=5000)
    assert worker.is_failed is True
    worker.submit(np.zeros((8, 8, 3), dtype=np.uint8))
    qtbot.wait(100)
    assert worker.is_failed is True
