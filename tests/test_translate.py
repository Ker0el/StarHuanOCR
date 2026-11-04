import pytest

from app import translate
from app.translate import TranslationError, build_payload, translate_text


def test_build_payload_shape():
    payload = build_payload("Hello world")
    assert payload["model"] == "deepseek-chat"
    assert payload["stream"] is False
    assert payload["messages"][-1]["content"] == "Hello world"
    assert payload["messages"][0]["role"] == "system"


def test_translate_returns_content(monkeypatch):
    monkeypatch.setattr(
        translate, "_post_json",
        lambda *a, **k: {"choices": [{"message": {"content": " 你好世界 "}}]},
    )
    assert translate_text("Hello world", "sk-test") == "你好世界"


def test_translate_without_key_raises():
    with pytest.raises(TranslationError):
        translate_text("Hello", "")


def test_translate_raises_on_unexpected_response(monkeypatch):
    monkeypatch.setattr(translate, "_post_json", lambda *a, **k: {"error": "bad"})
    with pytest.raises(TranslationError):
        translate_text("Hello", "sk-test")


def test_translate_wraps_network_errors(monkeypatch):
    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(translate, "_post_json", boom)
    with pytest.raises(TranslationError):
        translate_text("Hello", "sk-test")
