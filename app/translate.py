"""DeepSeek 翻译：官方 chat/completions 接口。"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, Signal

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
SYSTEM_PROMPT = (
    "你是翻译引擎。把用户提供的文本翻译成简体中文；"
    "如果原文已经是中文，则翻译成英文。只输出译文，不要任何解释或引号。"
)


class TranslationError(Exception):
    pass


def build_payload(text: str) -> dict:
    return {
        "model": DEEPSEEK_MODEL,
        "stream": False,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }


def _post_json(url: str, payload: dict, api_key: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def translate_text(text: str, api_key: str, timeout: float = 30.0) -> str:
    if not api_key.strip():
        raise TranslationError("未填写 DeepSeek API Key")
    if not text.strip():
        raise TranslationError("没有可翻译的内容")
    try:
        payload = _post_json(DEEPSEEK_URL, build_payload(text), api_key.strip(), timeout)
    except Exception as exc:
        raise TranslationError(f"请求失败：{exc}") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TranslationError(f"返回格式异常：{payload!r}") from exc
    return str(content).strip()


class Translator(QObject):
    """后台线程翻译，结果通过信号回主线程。"""

    finished = Signal(str)
    failed = Signal(str)

    def translate_async(self, text: str, api_key: str) -> None:
        threading.Thread(
            target=self._run, args=(text, api_key), daemon=True
        ).start()

    def _run(self, text: str, api_key: str) -> None:
        try:
            self.finished.emit(translate_text(text, api_key))
        except TranslationError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # 兜底，绝不让线程异常逃逸
            self.failed.emit(f"翻译失败：{exc}")
