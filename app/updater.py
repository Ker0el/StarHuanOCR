"""更新检查：只读 GitHub Release 的最新 tag。"""
from __future__ import annotations

import json
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from app import APP_VERSION

# 仓库地址；为空则整个功能关闭
REPO_OWNER = "Ker0el"
REPO_NAME = "StarHuanOCR"

_UA = f"StarHuanOCR/{APP_VERSION}"


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """'v1.2.3' -> (1,2,3)；带预发布后缀（含 '-'）或非语义化返回 None。"""
    text = tag.strip().lower()
    if text.startswith("v"):
        text = text[1:]
    if "-" in text:
        return None
    parts = text.split(".")
    if not 1 <= len(parts) <= 3:
        return None
    numbers = []
    for part in parts:
        if not part.isdigit():
            return None
        numbers.append(int(part))
    while len(numbers) < 3:
        numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def is_newer(remote: str, local: str) -> bool:
    remote_version = parse_version(remote)
    local_version = parse_version(local)
    if remote_version is None or local_version is None:
        return False
    return remote_version > local_version


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_update(
    current: str,
    owner: str = REPO_OWNER,
    repo: str = REPO_NAME,
    timeout: float = 3.0,
) -> str | None:
    """返回比 current 更新的远端 tag；任何异常或无需更新都返回 None。"""
    if not owner or not repo:
        return None
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        payload = _get_json(url, timeout)
    except Exception:
        return None
    tag = payload.get("tag_name") if isinstance(payload, dict) else None
    if not isinstance(tag, str):
        return None
    return tag if is_newer(tag, current) else None


class UpdateChecker(QObject):
    """后台线程里查一次，结果通过信号回主线程。"""

    found = Signal(str)

    def check_async(self, current: str = APP_VERSION) -> None:
        threading.Thread(target=self._run, args=(current,), daemon=True).start()

    def _run(self, current: str) -> None:
        tag = check_update(current)
        if tag:
            self.found.emit(tag)
