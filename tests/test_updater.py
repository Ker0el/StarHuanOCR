import pytest

from app import updater
from app.updater import check_update, is_newer, parse_version


@pytest.mark.parametrize(
    "remote,local,expected",
    [
        ("v1.2.0", "1.1.9", True),
        ("1.2.0", "1.2.0", False),
        ("v1.0.0", "1.2.0", False),
        ("v1.3.0-beta.1", "1.2.0", False),
    ],
)
def test_is_newer(remote, local, expected):
    assert is_newer(remote, local) is expected


def test_parse_version_strips_prefix():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.2") == (1, 2, 0)


def test_parse_version_rejects_prerelease():
    assert parse_version("v1.3.0-beta.1") is None


def test_check_update_returns_none_on_network_error(monkeypatch):
    monkeypatch.setattr(
        updater, "_get_json", lambda *a, **k: (_ for _ in ()).throw(OSError())
    )
    assert check_update("1.0.0", "o", "r") is None


def test_check_update_disabled_without_repo():
    assert check_update("1.0.0", "", "") is None
