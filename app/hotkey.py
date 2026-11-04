"""全局热键：解析、注册与 WM_HOTKEY 分发。"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
from typing import Iterable

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
}

_MODIFIER_ORDER: tuple[tuple[str, int], ...] = (
    ("Ctrl", MOD_CONTROL),
    ("Alt", MOD_ALT),
    ("Shift", MOD_SHIFT),
    ("Win", MOD_WIN),
)

_VK_F1 = 0x70


def _is_function_key(name: str) -> bool:
    upper = name.upper()
    if not upper.startswith("F") or not upper[1:].isdigit():
        return False
    return 1 <= int(upper[1:]) <= 12


def _key_to_vk(name: str) -> int:
    upper = name.upper()
    if _is_function_key(upper):
        return _VK_F1 + int(upper[1:]) - 1
    if len(name) == 1 and (name.isalpha() or name.isdigit()):
        return ord(upper)
    raise ValueError(f"无法识别的按键: {name}")


def parse_hotkey(text: str) -> tuple[int, int]:
    """把 "Ctrl+Alt+Q" / "F1" 解析成 (modifiers, vk)。非法或裸字母数字抛 ValueError。"""
    parts = [p.strip() for p in text.replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise ValueError("空热键")

    modifiers = 0
    for part in parts[:-1]:
        mod = _MODIFIERS.get(part.lower())
        if mod is None:
            raise ValueError(f"未知修饰键: {part}")
        modifiers |= mod

    key = parts[-1]
    vk = _key_to_vk(key)
    if modifiers == 0 and not _is_function_key(key):
        raise ValueError("热键至少需要一个修饰键，或使用 F1–F12")
    return modifiers, vk


def resolve_hotkey(text: str, default: str = "F1") -> str:
    """配置里的热键可能被手改成非法值：校验不过就回落到默认键。"""
    try:
        parse_hotkey(text)
    except (TypeError, ValueError):
        return default
    return text


def hotkey_to_string(mods: int, vk: int) -> str:
    """把 (modifiers, vk) 还原成可读字符串，顺序 Ctrl→Alt→Shift→Win。"""
    pieces = [name for name, bit in _MODIFIER_ORDER if mods & bit]
    if _VK_F1 <= vk < _VK_F1 + 12:
        pieces.append(f"F{vk - _VK_F1 + 1}")
    elif 0x30 <= vk <= 0x39:
        pieces.append(chr(vk))
    elif 0x41 <= vk <= 0x5A:
        pieces.append(chr(vk))
    else:
        pieces.append(f"VK{vk}")
    return "+".join(pieces)


class _NativeWatcher(QAbstractNativeEventFilter):
    def __init__(self, owner: "HotkeyManager") -> None:
        super().__init__()
        self._owner = owner

    def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt 命名)
        try:
            msg = ctypes.wintypes.MSG.from_address(int(message))
        except (TypeError, ValueError):
            return False, 0
        if msg.message == WM_HOTKEY and msg.wParam == self._owner.hotkey_id:
            self._owner.activated.emit()
            return True, 0
        return False, 0


class HotkeyManager(QObject):
    activated = Signal()

    _next_id = 0xA001

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        HotkeyManager._next_id += 1
        self.hotkey_id = HotkeyManager._next_id
        self.is_registered = False
        self._watcher = _NativeWatcher(self)
        self._filter_installed = False
        self._current: tuple[int, int] | None = None

    # --- Win32 边界（测试中可替换） ---
    def _call_register(self, mods: int, vk: int) -> int:
        return ctypes.windll.user32.RegisterHotKey(None, self.hotkey_id, mods, vk)

    def _call_unregister(self) -> None:
        try:
            ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)
        except OSError:
            pass

    # --- 对外接口 ---
    def register(self, text: str) -> bool:
        mods, vk = parse_hotkey(text)
        self.unregister()
        ok = bool(self._call_register(mods, vk))
        self.is_registered = ok
        if ok:
            self._current = (mods, vk)
            self._install_filter()
        return ok

    def unregister(self) -> None:
        if self.is_registered:
            self._call_unregister()
            self.is_registered = False
            self._current = None

    def _install_filter(self) -> None:
        if self._filter_installed:
            return
        from PySide6.QtCore import QCoreApplication

        app = QCoreApplication.instance()
        if app is None:
            return
        app.installNativeEventFilter(self._watcher)
        self._filter_installed = True
