"""星幻OCR 入口。"""
from __future__ import annotations

import ctypes
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app import APP_NAME, APP_VERSION
from app.config import load_config, save_config
from app.hotkey import HotkeyManager, resolve_hotkey
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
from app.updater import UpdateChecker
from app.ui.fonts import load_app_font
from app.ui.icon import load_icon
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


def selftest() -> int:
    """打包后验证模型与推理引擎能加载：写 selftest.txt 并返回退出码。"""
    from pathlib import Path

    out = Path(sys.executable).with_name("selftest.txt")
    try:
        device = choose_device(True, available_providers())
        tier = choose_tier("auto", device)
        engine = OcrEngine(DEFAULT_MODELS_DIR, device=device, tier=tier)
        engine.warmup()
        use_cls = getattr(engine._engine, "use_cls", None)
        result = f"ok device={engine.device} tier={engine.tier} use_cls={use_cls}"
        # 若同目录放了自检图片，再跑一次真实识别，验证离线可识别
        sample = out.parent / "selftest_image.png"
        if sample.exists():
            import cv2

            image = cv2.imread(str(sample))
            recognized = engine.recognize(image)
            result += f" text_len={len(recognized.text)}"
        code = 0
    except Exception as exc:
        result = f"failed: {exc!r}"
        code = 1
    try:
        out.write_text(result, encoding="utf-8")
    except OSError:
        pass
    return code


def wire_hotkey(hotkey: HotkeyManager, pipeline: Pipeline) -> None:
    """始终连接：即便启动时注册失败，之后在设置里改键成功也能用。"""
    hotkey.activated.connect(pipeline.trigger_capture)


def main() -> int:
    enable_dpi_awareness()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(load_icon())
    family = load_app_font()
    app.setProperty("app_font_family", family)
    app.setFont(QFont(family, 10))

    instance = SingleInstance()
    if not instance.try_acquire(APP_NAME):
        return 0

    apply_dark_theme()
    config = load_config()
    config.hotkey = resolve_hotkey(config.hotkey)

    worker = OcrWorker(lambda: build_engine(config))
    overlay = OverlayController()
    window = ResultWindow()
    chip = LoadingChip()
    tray = TrayIcon(config.hotkey)
    pipeline = Pipeline(config, worker, overlay, window, chip, tray)

    hotkey = HotkeyManager()
    wire_hotkey(hotkey, pipeline)
    if hotkey.register(config.hotkey):
        pass
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

    tray.update_requested.connect(
        lambda: (
            tray.notify(APP_NAME, "正在检查更新…", 1500),
            checker.check_async(APP_VERSION),
        )
    )
    tray.capture_requested.connect(pipeline.trigger_capture)
    tray.quit_requested.connect(app.quit)
    instance.activated.connect(pipeline.trigger_capture)
    pipeline.status_changed.connect(lambda msg: tray.notify(APP_NAME, msg, 2000))

    worker.start()

    if not config.first_run_done:
        tray.notify(APP_NAME, f"已启用，按 {config.hotkey} 框选取字。F1 已被本程序接管，可在设置里修改。")
        config.first_run_done = True
        save_config(config)

    checker = UpdateChecker()
    checker.found.connect(
        lambda tag: tray.notify(APP_NAME, f"发现新版本 {tag}，可在 GitHub Releases 查看。", 6000)
    )

    def maybe_check_updates() -> None:
        if not config.check_updates:
            return
        if time.time() - config.last_update_check < 86400:
            return
        config.last_update_check = time.time()
        save_config(config)
        checker.check_async(APP_VERSION)

    QTimer.singleShot(10_000, maybe_check_updates)

    app.aboutToQuit.connect(worker.stop)
    exit_code = app.exec()
    hotkey.unregister()
    instance.release()
    return exit_code


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
