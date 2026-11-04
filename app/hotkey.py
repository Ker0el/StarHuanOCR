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
_VK_F24 = 0x87

# 具名键：Win32 虚拟键码
_NAMED_KEYS: dict[str, int] = {
    "printscreen": 0x2C, "scrolllock": 0x91, "pause": 0x13,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "backspace": 0x08,
    "esc": 0x1B, "escape": 0x1B, "capslock": 0x14,
    "numpadmultiply": 0x6A, "numpadplus": 0x6B, "numpadminus": 0x6D,
    "numpaddecimal": 0x6E, "numpaddivide": 0x6F,
    ";": 0xBA, "semicolon": 0xBA, "=": 0xBB, "equal": 0xBB,
    ",": 0xBC, "comma": 0xBC, "-": 0xBD, "minus": 0xBD,
    ".": 0xBE, "period": 0xBE, "/": 0xBF, "slash": 0xBF,
    "`": 0xC0, "backquote": 0xC0,
    "[": 0xDB, "bracketleft": 0xDB, "\\": 0xDC, "backslash": 0xDC,
    "]": 0xDD, "bracketright": 0xDD, "'": 0xDE, "quote": 0xDE,
}

_VK_NAMES: dict[int, str] = {
    0x2C: "PrintScreen", 0x91: "ScrollLock", 0x13: "Pause",
    0x2D: "Insert", 0x2E: "Delete", 0x24: "Home", 0x23: "End",
    0x21: "PageUp", 0x22: "PageDown",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x20: "Space", 0x09: "Tab", 0x0D: "Enter", 0x08: "Backspace",
    0x1B: "Esc", 0x14: "CapsLock",
    0x6A: "NumpadMultiply", 0x6B: "NumpadPlus", 0x6D: "NumpadMinus",
    0x6E: "NumpadDecimal", 0x6F: "NumpadDivide",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}


def key_to_vk(name: str) -> int:
    """任意键名 -> Win32 虚拟键码。"""
    upper = name.upper()
    if upper.startswith("F") and upper[1:].isdigit():
        number = int(upper[1:])
        if 1 <= number <= 24:
            return _VK_F1 + number - 1
    if len(name) == 1 and name.isalnum():
        return ord(upper)
    lowered = name.lower()
    if lowered.startswith("numpad") and lowered[6:].isdigit() and len(lowered) == 7:
        return 0x60 + int(lowered[6])
    if lowered in _NAMED_KEYS:
        return _NAMED_KEYS[lowered]
    raise ValueError(f"无法识别的按键: {name}")


def vk_to_key_name(vk: int) -> str:
    if _VK_F1 <= vk <= _VK_F24:
        return f"F{vk - _VK_F1 + 1}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x60 <= vk <= 0x69:
        return f"Numpad{vk - 0x60}"
    return _VK_NAMES.get(vk, f"VK{vk}")


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
    return modifiers, key_to_vk(key)


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
    pieces.append(vk_to_key_name(vk))
    return "+".join(pieces)


_QT_MOD_TO_VK: dict[int, int] = {}


def _build_qt_key_map() -> dict[int, int]:
    from PySide6.QtCore import Qt

    names = {
        "Key_Print": 0x2C, "Key_ScrollLock": 0x91, "Key_Pause": 0x13,
        "Key_Insert": 0x2D, "Key_Delete": 0x2E, "Key_Home": 0x24, "Key_End": 0x23,
        "Key_PageUp": 0x21, "Key_PageDown": 0x22,
        "Key_Left": 0x25, "Key_Up": 0x26, "Key_Right": 0x27, "Key_Down": 0x28,
        "Key_Space": 0x20, "Key_Tab": 0x09, "Key_Return": 0x0D, "Key_Enter": 0x0D,
        "Key_Backspace": 0x08, "Key_Escape": 0x1B, "Key_CapsLock": 0x14,
        "Key_Semicolon": 0xBA, "Key_Equal": 0xBB, "Key_Comma": 0xBC,
        "Key_Minus": 0xBD, "Key_Period": 0xBE, "Key_Slash": 0xBF,
        "Key_QuoteLeft": 0xC0, "Key_BracketLeft": 0xDB, "Key_Backslash": 0xDC,
        "Key_BracketRight": 0xDD, "Key_Apostrophe": 0xDE,
        # 小键盘运算符在 Qt 里是小写枚举名
        "Key_multiply": 0x6A, "Key_plus": 0x6B, "Key_minus": 0x6D,
        "Key_comma": 0x6E, "Key_division": 0x6F,
    }
    mapping: dict[int, int] = {}
    for name, vk in names.items():
        value = getattr(Qt.Key, name, None)
        if value is not None:
            mapping[int(value)] = vk
    return mapping


def qt_key_to_vk(key: int, modifiers=None) -> int | None:
    """Qt 键码 -> Win32 虚拟键码；无法映射（纯修饰键等）返回 None。"""
    from PySide6.QtCore import Qt

    if not _QT_MOD_TO_VK:
        _QT_MOD_TO_VK.update(_build_qt_key_map())

    K = Qt.Key
    if K.Key_F1 <= key <= K.Key_F35:
        number = key - K.Key_F1 + 1
        return 0x70 + number - 1 if number <= 24 else None
    if K.Key_A <= key <= K.Key_Z:
        return key
    if K.Key_0 <= key <= K.Key_9:
        if modifiers is not None and (modifiers & Qt.KeyboardModifier.KeypadModifier):
            return 0x60 + (key - K.Key_0)
        return key
    return _QT_MOD_TO_VK.get(key)


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
