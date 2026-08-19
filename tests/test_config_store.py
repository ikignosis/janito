"""
Tests for the ConfigStore class (janito.general_config).

Covers the class-level read/write primitives: merged loads across the
resolution chain, provider-scoped set/unset with empty-provider cleanup, and
write-target-only semantics (global entries are never copied into local files).
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
from janito.config_keys import PROVIDER_SCOPED_KEYS
from janito.config_store import ConfigStore


@pytest.fixture(autouse=True)
def _reset_local_mode():
    """Ensure -l/--local mode never leaks into other test modules."""
    yield
    config_dir_mod.set_local_config_mode(False)


def _point_at(monkeypatch, tmp_path):
    base = tmp_path / "janito"
    monkeypatch.setattr(config_dir_mod, "_config_dir", base)
    return base


def _project_cwd(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    monkeypatch.chdir(project)
    return project


if pytest is not None:

    def test_get_set_roundtrip(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = ConfigStore()
        store.set("theme", "dark")
        assert store.get("theme") == "dark"
        assert (base / "config.json").exists()

    def test_provider_scoped_set_unset(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = ConfigStore()
        store.set("openai.model", "gpt-4")
        assert store.get("openai.model") == "gpt-4"
        assert json.loads((base / "config.json").read_text()) == {
            "providers": {"openai": {"model": "gpt-4"}}
        }
        # Unsetting the last key removes the empty provider dict entirely.
        assert store.unset("openai.model") is True
        assert store.get("openai.model") is None
        assert json.loads((base / "config.json").read_text()) == {}
        assert store.unset("openai.model") is False

    def test_provider_scoped_set_requires_scoped_key(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = ConfigStore()
        # "unknown.key" is not in PROVIDER_SCOPED_KEYS -> stored as a flat key.
        store.set("unknown.key", "value")
        assert store.get("unknown.key") == "value"
        assert json.loads((base / "config.json").read_text()) == {
            "unknown.key": "value"
        }
        assert "unknown.key" not in PROVIDER_SCOPED_KEYS

    def test_flat_set_after_provider_scoped(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = ConfigStore()
        store.set("openai.model", "gpt-4")
        store.set("provider", "openai")
        assert store.get("provider") == "openai"
        assert store.get("openai.model") == "gpt-4"
        assert json.loads((base / "config.json").read_text()) == {
            "provider": "openai",
            "providers": {"openai": {"model": "gpt-4"}},
        }

    def test_merge_local_wins(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        _project_cwd(monkeypatch, tmp_path)

        global_store = ConfigStore()
        config_dir_mod.set_local_config_mode(False)
        global_store.set("theme", "global")
        global_store.set("provider", "openai")

        config_dir_mod.set_local_config_mode(True)
        local_store = ConfigStore()
        local_store.set("theme", "local")

        assert global_store.load()["theme"] == "local"
        assert global_store.load()["provider"] == "openai"

    def test_writes_target_local_only(monkeypatch, tmp_path):
        """In -l/--local mode, writes never copy global entries into the local
        file (the local file stores only what was written locally)."""
        _point_at(monkeypatch, tmp_path)
        project = _project_cwd(monkeypatch, tmp_path)

        config_dir_mod.set_local_config_mode(False)
        global_store = ConfigStore()
        global_store.set("theme", "global")
        global_store.set("provider", "openai")

        config_dir_mod.set_local_config_mode(True)
        local_store = ConfigStore()
        local_store.set("theme", "local")

        local_config = json.loads((project / ".janito" / "config.json").read_text())
        assert "theme" in local_config
        assert "provider" not in local_config

    def test_load_missing_returns_empty(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        assert ConfigStore().load() == {}

    def test_load_invalid_json_raises(monkeypatch, tmp_path):
        """`load()` mirrors the historical merged load: an invalid JSON file
        propagates `json.JSONDecodeError` (the docstring's "invalid" note
        predates the merged implementation)."""
        base = _point_at(monkeypatch, tmp_path)
        (base / "config.json").parent.mkdir(parents=True, exist_ok=True)
        (base / "config.json").write_text("{ broken")
        with pytest.raises(json.JSONDecodeError):
            ConfigStore().load()

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def chdir(self, path):
                import os

                self._undo.append((os, "getcwd", os.getcwd()))
                os.chdir(path)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                with tempfile.TemporaryDirectory() as d:
                    fn(mp, Path(d))
                mp.restore()
                config_dir_mod.set_local_config_mode(False)
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
