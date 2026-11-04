"""星幻OCR 入口。"""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QApplication

from app import APP_NAME
from app.config import load_config, save_config
from app.hotkey import HotkeyManager
from app.ocr.engine import (
    DEFAULT_MODELS_DIR,
    OcrEngine,
    OcrWorker,
    available_providers,
    choose_device,
    choose_tier,
)
from app.overlay import OverlayController
from app.pipeline import Pipeline
from app.single_instance import SingleInstance
from app.ui.result_window import LoadingChip, ResultWindow
from app.ui.settings_window import SettingsWindow
from app.ui.theme import apply_dark_theme
from app.ui.tray import TrayIcon


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor v2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def build_engine(config) -> OcrEngine:
    device = choose_device(config.prefer_gpu, available_providers())
    tier = choose_tier(config.precision, device)
    return OcrEngine(DEFAULT_MODELS_DIR, device=device, tier=tier)


def main() -> int:
    enable_dpi_awareness()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    instance = SingleInstance()
    if not instance.try_acquire(APP_NAME):
        return 0

    apply_dark_theme()
    config = load_config()

    worker = OcrWorker(lambda: build_engine(config))
    overlay = OverlayController()
    window = ResultWindow()
    chip = LoadingChip()
    tray = TrayIcon(config.hotkey)
    pipeline = Pipeline(config, worker, overlay, window, chip, tray)

    hotkey = HotkeyManager()
    if hotkey.register(config.hotkey):
        hotkey.activated.connect(pipeline.trigger_capture)
    else:
        tray.notify(APP_NAME, f"快捷键 {config.hotkey} 注册失败，可能已被占用，请在设置里换一个。")

    settings_window = SettingsWindow()

    def open_settings() -> None:
        device = choose_device(config.prefer_gpu, available_providers())
        settings_window.open(config, device)

    def on_settings_changed(updated) -> None:
        if updated.hotkey != config.hotkey:
            previous = config.hotkey
            if hotkey.register(updated.hotkey):
                config.hotkey = updated.hotkey
            else:
                hotkey.register(previous)
                updated.hotkey = previous
                tray.notify(APP_NAME, f"快捷键 {updated.hotkey} 被占用，已保留原键。")
            tray.set_hotkey_text(config.hotkey)

        if updated.precision != config.precision or updated.prefer_gpu != config.prefer_gpu:
            config.precision = updated.precision
            config.prefer_gpu = updated.prefer_gpu
            pipeline.replace_worker(OcrWorker(lambda: build_engine(config)))
            tray.notify(APP_NAME, "识别引擎已按新设置重启。", 2000)

        config.auto_copy = updated.auto_copy
        config.show_result = updated.show_result
        config.autostart = updated.autostart
        config.check_updates = updated.check_updates
        save_config(config)
    settings_window.changed.connect(on_settings_changed)
    settings_window.hotkey_rejected.connect(lambda msg: tray.notify(APP_NAME, f"快捷键无效：{msg}"))
    tray.settings_requested.connect(open_settings)

    tray.capture_requested.connect(pipeline.trigger_capture)
    tray.quit_requested.connect(app.quit)
    instance.activated.connect(pipeline.trigger_capture)
    pipeline.status_changed.connect(lambda msg: tray.notify(APP_NAME, msg, 2000))

    worker.start()

    if not config.first_run_done:
        tray.notify(APP_NAME, f"已启用，按 {config.hotkey} 框选取字。F1 已被本程序接管，可在设置里修改。")
        config.first_run_done = True
        save_config(config)

    app.aboutToQuit.connect(worker.stop)
    exit_code = app.exec()
    hotkey.unregister()
    instance.release()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
