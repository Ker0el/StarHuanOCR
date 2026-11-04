import pytest

from app.hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    HotkeyManager,
    hotkey_to_string,
    parse_hotkey,
)


def test_parse_function_key():
    assert parse_hotkey("F1") == (0, 0x70)
    assert parse_hotkey("f12") == (0, 0x7B)


def test_parse_modifier_combo():
    mods, vk = parse_hotkey("Ctrl+Alt+Q")
    assert mods == MOD_CONTROL | MOD_ALT
    assert vk == ord("Q")


def test_bare_letter_is_rejected():
    with pytest.raises(ValueError):
        parse_hotkey("Q")


def test_bare_digit_is_rejected():
    with pytest.raises(ValueError):
        parse_hotkey("5")


def test_roundtrip_string():
    mods, vk = parse_hotkey("Ctrl+Shift+F5")
    assert hotkey_to_string(mods, vk) == "Ctrl+Shift+F5"


def test_register_returns_false_when_win32_fails(monkeypatch, qapp):
    mgr = HotkeyManager()
    monkeypatch.setattr(mgr, "_call_register", lambda mods, vk: 0)
    assert mgr.register("Ctrl+Alt+Q") is False


def test_resolve_hotkey_falls_back_on_invalid_config():
    from app.hotkey import resolve_hotkey

    assert resolve_hotkey("Ctrl+Alt+Q") == "Ctrl+Alt+Q"
    assert resolve_hotkey("Ctrl+Space") == "F1"
    assert resolve_hotkey("") == "F1"
