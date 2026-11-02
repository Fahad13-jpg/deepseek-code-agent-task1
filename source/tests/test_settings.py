import json
import os

import pytest

from codeagent import settings


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_dpapi_roundtrip_and_no_plaintext_at_rest(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "settings_path", lambda: tmp_path / "settings.json")
    key = "sk-test-value-never-store-in-plain-text"
    settings.save_settings({"output": "some-folder"}, key, remember=True)
    assert key not in (tmp_path / "settings.json").read_text()
    assert settings.load_settings()["api_key"] == key
    settings.save_settings({"output": "some-folder"}, key, remember=False)
    assert "protected_key" not in json.loads((tmp_path / "settings.json").read_text())


def test_corrupt_preferences_do_not_crash(tmp_path, monkeypatch):
    file = tmp_path / "settings.json"
    file.write_text("{broken")
    monkeypatch.setattr(settings, "settings_path", lambda: file)
    assert settings.load_settings() == {}
