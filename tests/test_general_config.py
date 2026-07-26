"""
Tests for provider-scoped configuration in general_config.

The ``model`` and ``endpoint`` config keys are stored per-provider under
``providers.<provider>.model`` and ``providers.<provider>.endpoint`` so that each
provider can have its own default model and endpoint. The provider is resolved
from the ``--provider`` CLI argument first, then from the configured ``provider``
value.

Note: Legacy flat keys (e.g. "openai.model") are NOT automatically migrated.
Users with old configs must manually update them to the new nested structure.
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_dir as config_dir_mod
import janito.general_config as gc
from janito.general_config import ProviderRequiredError

try:
    import pytest
except ImportError:  # pragma: no cover - pytest is a dev dependency
    pytest = None


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    # The config dir is the single source of truth for all config file paths,
    # so override it (instead of the legacy CONFIG_PATH constant).
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _read_config(config_path):
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return json.load(f)


if pytest is not None:

    def test_set_model_without_provider_errors(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ProviderRequiredError):
            gc.set_config_from_cli("model=gpt-4")
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_set_model_with_cli_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        key, value = gc.set_config_from_cli("model=gpt-4", "openai")
        assert key == "openai.model"
        assert value == "gpt-4"
        assert _read_config(config_path) == {
            "providers": {"openai": {"model": "gpt-4"}}
        }

    def test_set_model_uses_configured_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=minimax")
        key, _ = gc.set_config_from_cli("model=abab6.5")
        assert key == "minimax.model"
        assert _read_config(config_path)["providers"]["minimax"]["model"] == "abab6.5"

    def test_cli_provider_overrides_configured_provider(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=minimax")
        key, _ = gc.set_config_from_cli("model=gpt-4", "openai")
        assert key == "openai.model"

    def test_provider_is_normalized(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        key, _ = gc.set_config_from_cli("model=gpt-4", "  OpenAI ")
        assert key == "openai.model"

    def test_get_model_per_provider(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("model=gpt-4", "openai")
        gc.set_config_from_cli("model=abab6.5", "minimax")
        assert gc.get_config_from_cli("model", "openai") == "gpt-4"
        assert gc.get_config_from_cli("model", "minimax") == "abab6.5"

    def test_get_model_without_provider_errors(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        # A config file must exist for --get; write an unrelated (non-scoped) key.
        gc.set_config_value("theme", "dark")
        with pytest.raises(ProviderRequiredError):
            gc.get_config_from_cli("model")
        assert config_path.exists()

    def test_load_model_from_config(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=minimax")
        gc.set_config_from_cli("model=abab6.5")
        gc.set_config_from_cli("model=gpt-4", "openai")
        # Active provider (from config) is minimax
        assert gc.load_model_from_config() == "abab6.5"
        # CLI provider override wins
        assert gc.load_model_from_config("openai") == "gpt-4"
        # Unknown provider has no model
        assert gc.load_model_from_config("unknown") is None

    def test_load_model_without_provider_returns_none(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("model=gpt-4", "openai")
        # No provider configured and none supplied -> cannot resolve -> None
        assert gc.load_model_from_config() is None

    def test_unset_model_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("model=gpt-4", "openai")
        gc.set_config_from_cli("model=abab6.5", "minimax")
        assert gc.unset_config_key_from_cli("model", "openai") is True
        config = _read_config(config_path)
        assert "openai" not in config.get("providers", {})
        assert config["providers"]["minimax"]["model"] == "abab6.5"
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("model", "openai") is False

    def test_unset_model_without_provider_errors(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("model=gpt-4", "openai")
        with pytest.raises(ProviderRequiredError):
            gc.unset_config_key_from_cli("model")

    def test_non_scoped_keys_unaffected(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        key, _ = gc.set_config_from_cli("provider=openai")
        assert key == "provider"
        assert gc.get_config_from_cli("provider") == "openai"
        assert gc.unset_config_key_from_cli("provider") is True
        assert _read_config(config_path) == {}

    def test_set_endpoint_without_provider_errors(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ProviderRequiredError):
            gc.set_config_from_cli("endpoint=http://x/v1")
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_set_endpoint_with_cli_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        key, value = gc.set_config_from_cli("endpoint=http://x/v1", "custom")
        assert key == "custom.endpoint"
        assert value == "http://x/v1"
        assert _read_config(config_path) == {
            "providers": {"custom": {"endpoint": "http://x/v1"}}
        }

    def test_set_endpoint_uses_configured_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=custom")
        key, _ = gc.set_config_from_cli("endpoint=http://x/v1")
        assert key == "custom.endpoint"
        assert (
            _read_config(config_path)["providers"]["custom"]["endpoint"]
            == "http://x/v1"
        )

    def test_get_endpoint_per_provider(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("endpoint=http://a/v1", "custom")
        gc.set_config_from_cli("endpoint=http://b/v1", "openai")
        assert gc.get_config_from_cli("endpoint", "custom") == "http://a/v1"
        assert gc.get_config_from_cli("endpoint", "openai") == "http://b/v1"

    def test_load_endpoint_from_config_per_provider(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=custom")
        gc.set_config_from_cli("endpoint=http://a/v1", "custom")
        gc.set_config_from_cli("endpoint=http://b/v1", "openai")
        # Active provider (from config) is custom
        assert gc.load_endpoint_from_config() == "http://a/v1"
        # CLI provider override wins
        assert gc.load_endpoint_from_config("openai") == "http://b/v1"
        # Unknown provider has no endpoint (and no legacy top-level value)
        assert gc.load_endpoint_from_config("unknown") is None

    def test_load_endpoint_legacy_top_level_fallback(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        # Write a legacy top-level 'endpoint' key directly.
        gc.set_config_value("endpoint", "http://legacy/v1")
        # No provider-scoped endpoint exists, so the legacy key is honored.
        assert gc.load_endpoint_from_config("custom") == "http://legacy/v1"

    def test_unset_endpoint_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("endpoint=http://a/v1", "custom")
        gc.set_config_from_cli("endpoint=http://b/v1", "openai")
        assert gc.unset_config_key_from_cli("endpoint", "custom") is True
        config = _read_config(config_path)
        assert "custom" not in config.get("providers", {})
        assert config["providers"]["openai"]["endpoint"] == "http://b/v1"
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("endpoint", "custom") is False

    def test_endpoint_config_key_helper():
        assert gc.endpoint_config_key("custom") == "custom.endpoint"
        assert gc.endpoint_config_key("  Custom ") == "custom.endpoint"

    def test_model_config_key_helper():
        assert gc.model_config_key("openai") == "openai.model"
        assert gc.model_config_key("  MiniMax ") == "minimax.model"

    def test_set_context_window_size_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=openai")
        gc.set_config_from_cli("context-window-size=8192")
        gc.set_config_from_cli("context-window-size=4096", "minimax")
        # Each provider has its own context-window-size
        assert gc.load_context_window_size("openai") == 8192
        assert gc.load_context_window_size("minimax") == 4096
        # Verify storage structure
        config = _read_config(config_path)
        assert config["providers"]["openai"]["context-window-size"] == 8192
        assert config["providers"]["minimax"]["context-window-size"] == 4096

    def test_unset_context_window_size_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("context-window-size=8192", "openai")
        gc.set_config_from_cli("context-window-size=4096", "minimax")
        assert gc.unset_config_key_from_cli("context-window-size", "openai") is True
        config = _read_config(config_path)
        assert "openai" not in config.get("providers", {})
        assert config["providers"]["minimax"]["context-window-size"] == 4096
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("context-window-size", "openai") is False

    def test_determine_provider_priority(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=minimax")
        # CLI provider takes priority over configured provider
        assert gc.determine_provider("openai") == "openai"
        # Falls back to configured provider
        assert gc.determine_provider() == "minimax"
        # No provider anywhere
        gc.unset_config_value("provider")
        assert gc.determine_provider() is None

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
