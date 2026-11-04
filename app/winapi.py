"""Win32 相关：开机自启注册表。"""
from __future__ import annotations

import sys

import winreg

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE = "StarHuanOCR"


def autostart_command(exe_path: str | None = None) -> str:
    path = exe_path or sys.executable
    return f'"{path}"'


def _set_run_value(path: str, name: str, value: str) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _delete_run_value(path: str, name: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def set_autostart(enabled: bool, exe_path: str | None = None) -> None:
    try:
        if enabled:
            _set_run_value(AUTOSTART_KEY, AUTOSTART_VALUE, autostart_command(exe_path))
        else:
            _delete_run_value(AUTOSTART_KEY, AUTOSTART_VALUE)
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_VALUE)
            return True
    except OSError:
        return False
