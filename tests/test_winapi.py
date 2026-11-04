from app import winapi
from app.winapi import autostart_command, set_autostart


def test_autostart_command_quotes_path():
    assert autostart_command(r"C:\Program Files\StarHuanOCR\StarHuanOCR.exe") == \
        '"C:\Program Files\StarHuanOCR\StarHuanOCR.exe"'


def test_set_autostart_writes_and_removes(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "_set_run_value", lambda path, name, val: calls.append((name, val)))
    monkeypatch.setattr(winapi, "_delete_run_value", lambda path, name: calls.append((name, None)))
    set_autostart(True, "C:/x.exe")
    set_autostart(False, "C:/x.exe")
    assert calls == [("StarHuanOCR", '"C:/x.exe"'), ("StarHuanOCR", None)]
