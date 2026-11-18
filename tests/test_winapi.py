from app import winapi
from app.winapi import autostart_command, set_autostart, sync_autostart


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


def test_sync_autostart_writes_when_registry_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "read_autostart", lambda: None)
    monkeypatch.setattr(winapi, "set_autostart", lambda enabled, exe=None: calls.append(enabled))
    sync_autostart(True, "C:/x.exe")
    assert calls == [True]


def test_sync_autostart_refreshes_changed_path(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "read_autostart", lambda: '"C:/old.exe"')
    monkeypatch.setattr(winapi, "set_autostart", lambda enabled, exe=None: calls.append(enabled))
    sync_autostart(True, "C:/new.exe")
    assert calls == [True]


def test_sync_autostart_noop_when_already_synced(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "read_autostart", lambda: '"C:/x.exe"')
    monkeypatch.setattr(winapi, "set_autostart", lambda enabled, exe=None: calls.append(enabled))
    sync_autostart(True, "C:/x.exe")
    assert calls == []


def test_sync_autostart_removes_when_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(winapi, "read_autostart", lambda: '"C:/x.exe"')
    monkeypatch.setattr(winapi, "set_autostart", lambda enabled, exe=None: calls.append(enabled))
    sync_autostart(False)
    assert calls == [False]
