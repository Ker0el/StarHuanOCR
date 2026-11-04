from app.config import Config, load_config, save_config


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "none.json")
    assert cfg.hotkey == "F1"
    assert cfg.auto_copy is True
    assert cfg.precision == "auto"


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    cfg = Config(hotkey="Ctrl+Alt+Q", auto_copy=False)
    save_config(cfg, p)
    assert load_config(p).hotkey == "Ctrl+Alt+Q"
    assert load_config(p).auto_copy is False


def test_unknown_or_corrupt_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{ not json", encoding="utf-8")
    assert load_config(p).hotkey == "F1"


def test_unknown_keys_are_ignored(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"hotkey": "F2", "legacy": 1}', encoding="utf-8")
    assert load_config(p).hotkey == "F2"


def test_translation_defaults_and_roundtrip(tmp_path):
    cfg = load_config(tmp_path / "none.json")
    assert cfg.translation_enabled is False
    assert cfg.deepseek_api_key == ""
    assert cfg.auto_translate is False

    p = tmp_path / "c.json"
    cfg.translation_enabled = True
    cfg.deepseek_api_key = "sk-abc"
    cfg.auto_translate = True
    save_config(cfg, p)
    loaded = load_config(p)
    assert loaded.translation_enabled is True
    assert loaded.deepseek_api_key == "sk-abc"
    assert loaded.auto_translate is True
