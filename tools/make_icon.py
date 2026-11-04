"""生成 assets/icon.ico（黑底蓝色星形）。"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ui.icon import ICON_PATH, draw_icon  # noqa: E402


def main() -> int:
    app = QGuiApplication(sys.argv)
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    ok = draw_icon(256).save(str(ICON_PATH), "ico")
    print(f"{ICON_PATH} saved={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
