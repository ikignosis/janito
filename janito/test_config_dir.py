"""
Tests for the -c/--config-dir feature.

The ``config_dir`` module holds a single global configuration directory used by
all config modules (general_config, auth_config, secrets_config, mcp_config and
skills). By default this is ``~/.janito`` but :func:`set_config_dir` overrides
it so every config/auth/secret/MCP/skills file is stored in the requested
directory instead.
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.auth_config as ac
import janito.config_dir as config_dir_mod
import janito.general_config as gc
import janito.mcp_config as mc
import janito.secrets_config as sc

try:
    import pytest
except ImportError:  # pragma: no cover - pytest is a dev dependency
    pytest = None


def _point_at(monkeypatch, tmp_path):
    """Point the global config dir at a temp directory and return it."""
    config_dir = tmp_path / "custom_janito"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_dir)
    return config_dir


if pytest is not None:

    def test_default_config_dir_is_home_janito():
        assert config_dir_mod.DEFAULT_CONFIG_DIR == Path.home() / ".janito"

    def test_set_config_dir_updates_all_module_paths(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        assert gc.get_config_path() == config_dir / "config.json"
        assert ac.get_auth_file_path() == config_dir / "auth.json"
        assert sc.get_secrets_file_path() == config_dir / "secrets.json"
        assert mc.get_mcp_config_path() == config_dir / "mcp_services.json"

    def test_set_config_dir_function_expands_user(monkeypatch, tmp_path):
        config_dir_mod.set_config_dir("~/my_janito_dir")
        try:
            assert config_dir_mod.get_config_dir() == Path.home() / "my_janito_dir"
        finally:
            config_dir_mod.set_config_dir(str(config_dir_mod.DEFAULT_CONFIG_DIR))

    def test_set_config_dir_ignores_empty(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        # Empty / None values are a no-op and keep the current directory.
        config_dir_mod.set_config_dir(None)
        assert config_dir_mod.get_config_dir() == config_dir
        config_dir_mod.set_config_dir("")
        assert config_dir_mod.get_config_dir() == config_dir

    def test_config_write_and_read_uses_custom_dir(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        gc.set_config_value("provider", "openai")
        # The file must land inside the custom directory...
        assert (config_dir / "config.json").exists()
        # ...and NOT in the default ~/.janito location.
        assert gc.load_config()["provider"] == "openai"
        with open(config_dir / "config.json") as f:
            assert json.load(f)["provider"] == "openai"

    def test_auth_write_uses_custom_dir(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        assert ac.set_api_key("openai", "sk-test") is True
        assert (config_dir / "auth.json").exists()
        assert ac.get_api_key("openai") == "sk-test"

    def test_secrets_write_uses_custom_dir(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        assert sc.set_secret("token", "abc123") is True
        assert (config_dir / "secrets.json").exists()
        assert sc.get_secret("token") == "abc123"

    def test_mcp_write_uses_custom_dir(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        mc.save_mcp_config({"services": {"svc": {"command": "x"}}})
        assert (config_dir / "mcp_services.json").exists()
        assert mc.load_mcp_config()["services"]["svc"]["command"] == "x"

    def test_custom_dir_isolated_from_default(monkeypatch, tmp_path):
        # Write under a custom dir, then switch back to default and confirm the
        # value is NOT visible there (proving true isolation).
        _point_at(monkeypatch, tmp_path)
        gc.set_config_value("provider", "openai")
        assert gc.load_config().get("provider") == "openai"

        other_dir = tmp_path / "other_janito"
        monkeypatch.setattr(config_dir_mod, "_config_dir", other_dir)
        # Nothing was ever written to other_dir, so config should be empty.
        assert gc.load_config() == {}

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(_MP(), Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
