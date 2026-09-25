import json

import common
from common import DEFAULTS, Config, validate_config


def test_defaults_when_missing(tmp_path):
    cfg = Config(tmp_path / "config.json")
    assert cfg["speed"] == DEFAULTS["speed"]
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["speed"] == DEFAULTS["speed"]


def test_set_persists(tmp_path):
    path = tmp_path / "config.json"
    Config(path).set("speed", 1.2)
    assert Config(path)["speed"] == 1.2
    assert not (tmp_path / "config.json.tmp").exists()


def test_broken_file_is_kept_aside(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    cfg = Config(path)
    assert cfg["speed"] == DEFAULTS["speed"]
    assert (tmp_path / "config.json.broken").read_text(encoding="utf-8") == "{ not json"


def test_non_object_json_is_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert Config(path)["sounds"] is True
    assert (tmp_path / "config.json.broken").exists()


def test_bom_is_accepted(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"speed": 0.9}', encoding="utf-8-sig")  # так зберігає Блокнот
    assert Config(path)["speed"] == 0.9


def test_validate_types():
    good = validate_config({"speed": "fast", "sounds": 1, "cleanup_timeout": 5, "mic_device": 3, "future_key": "x"})
    assert "speed" not in good  # рядок замість числа
    assert "sounds" not in good  # 1 — не bool
    assert good["cleanup_timeout"] == 5
    assert good["mic_device"] == 3  # стандартне None — приймаємо будь-що
    assert good["future_key"] == "x"  # невідомі ключі зберігаємо


def test_redact_hides_text_by_default():
    assert common.redact("секрет", {"log_text": False}) == "<6 симв.>"
    assert common.redact("секрет", {"log_text": True}) == "секрет"


def test_history_rotates(tmp_path):
    path = tmp_path / "history.txt"
    path.write_text("x" * 100, encoding="utf-8")
    common.append_history("новий рядок", path=path, max_bytes=50)
    assert (tmp_path / "history.1.txt").read_text(encoding="utf-8") == "x" * 100
    assert path.read_text(encoding="utf-8").endswith("новий рядок\n")
