"""深色主题与 Windows 亚克力效果。"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtWidgets import QWidget

ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(_AccentPolicy)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def apply_dark_theme() -> None:
    try:
        from qfluentwidgets import Theme, setTheme

        setTheme(Theme.DARK)
    except Exception:
        pass


def enable_acrylic(widget: QWidget, tint: int = 0x99202020) -> None:
    """给窗口加 DWM 亚克力背景；失败时静默返回。"""
    try:
        hwnd = wintypes.HWND(int(widget.winId()))
        policy = _AccentPolicy(ACCENT_ENABLE_ACRYLICBLURBEHIND, 2, tint, 0)
        data = _WindowCompositionAttributeData(
            WCA_ACCENT_POLICY, ctypes.pointer(policy), ctypes.sizeof(policy)
        )
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass
