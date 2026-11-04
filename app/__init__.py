"""星幻OCR —— Windows 截图取字工具。"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "星幻OCR"
APP_VERSION = "0.1.0"

_appdata = os.environ.get("APPDATA") or str(Path.home())
CONFIG_DIR = Path(_appdata) / "StarHuanOCR"
CONFIG_PATH = CONFIG_DIR / "config.json"
LOG_DIR = CONFIG_DIR / "logs"
