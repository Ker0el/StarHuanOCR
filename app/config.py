"""配置的读写与默认值。"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from app import CONFIG_PATH


@dataclass
class Config:
    hotkey: str = "F1"
    auto_copy: bool = True
    show_result: bool = True
    prefer_gpu: bool = True
    precision: str = "auto"
    autostart: bool = False
    check_updates: bool = True
    last_update_check: float = 0.0
    latest_known_version: str = ""
    first_run_done: bool = False
    translation_enabled: bool = False
    deepseek_api_key: str = ""
    auto_translate: bool = False


def load_config(path: Path = CONFIG_PATH) -> Config:
    """读取配置；文件缺失、损坏或字段未知时回落默认值。"""
    cfg = Config()
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return cfg
    if not isinstance(raw, dict):
        return cfg
    known = {f.name for f in fields(Config)}
    for key, value in raw.items():
        if key not in known:
            continue
        current = getattr(cfg, key)
        if isinstance(current, bool):
            if isinstance(value, bool):
                setattr(cfg, key, value)
        elif isinstance(current, (int, float)):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                setattr(cfg, key, type(current)(value))
        elif isinstance(current, str):
            if isinstance(value, str):
                setattr(cfg, key, value)
    return cfg


def save_config(cfg: Config, path: Path = CONFIG_PATH) -> None:
    """原子写入配置：先写临时文件再 os.replace。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(asdict(cfg), fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
