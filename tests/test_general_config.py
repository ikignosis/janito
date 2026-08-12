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

import pytest

import janito.config_dir as config_dir_mod
import janito.general_config as gc
from janito.general_config import ProviderRequiredError

try:
    import anthropic  # noqa: F401

    _HAS_ANTHROPIC = True
except ModuleNotFoundError:
    _HAS_ANTHROPIC = False

# The "aborts without the package" guard test only applies when the optional
# `anthropic` package is missing; skip it when it is installed.
requires_no_anthropic = pytest.mark.skipif(
    _HAS_ANTHROPIC, reason="anthropic package is installed (guard not exercised)"
)


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

    def test_set_max_output_tokens_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=openai")
        gc.set_config_from_cli("max-output-tokens=8192")
        gc.set_config_from_cli("max-output-tokens=4096", "minimax")
        # Each provider has its own max-output-tokens
        assert gc.load_max_output_tokens("openai") == 8192
        assert gc.load_max_output_tokens("minimax") == 4096
        # Verify storage structure
        config = _read_config(config_path)
        assert config["providers"]["openai"]["max-output-tokens"] == 8192
        assert config["providers"]["minimax"]["max-output-tokens"] == 4096

    def test_unset_max_output_tokens_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("max-output-tokens=8192", "openai")
        gc.set_config_from_cli("max-output-tokens=4096", "minimax")
        assert gc.unset_config_key_from_cli("max-output-tokens", "openai") is True
        config = _read_config(config_path)
        assert "openai" not in config.get("providers", {})
        assert config["providers"]["minimax"]["max-output-tokens"] == 4096
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("max-output-tokens", "openai") is False

    def test_max_input_tokens_config_key_helper():
        assert gc.max_input_tokens_config_key("openai") == "openai.max-input-tokens"
        assert gc.max_input_tokens_config_key("  OpenAI ") == "openai.max-input-tokens"

    def test_set_max_input_tokens_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=openai")
        gc.set_config_from_cli("max-input-tokens=128000")
        gc.set_config_from_cli("max-input-tokens=256000", "minimax")
        # Each provider has its own max-input-tokens
        assert gc.load_max_input_tokens("openai") == 128000
        assert gc.load_max_input_tokens("minimax") == 256000
        # Values are stored as ints (coerced via INT_VALUED_KEYS)
        key, value = gc.set_config_from_cli("max-input-tokens=200000", "deepseek")
        assert key == "deepseek.max-input-tokens"
        assert value == 200000
        config = _read_config(config_path)
        assert config["providers"]["openai"]["max-input-tokens"] == 128000
        assert config["providers"]["minimax"]["max-input-tokens"] == 256000
        assert config["providers"]["deepseek"]["max-input-tokens"] == 200000

    def test_set_max_input_tokens_rejects_non_int(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ValueError) as exc:
            gc.set_config_from_cli("max-input-tokens=one-hundred-thousand", "openai")
        assert "integer" in str(exc.value)
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_unset_max_input_tokens_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("max-input-tokens=128000", "openai")
        gc.set_config_from_cli("max-input-tokens=256000", "minimax")
        assert gc.unset_config_key_from_cli("max-input-tokens", "openai") is True
        config = _read_config(config_path)
        assert "openai" not in config.get("providers", {})
        assert config["providers"]["minimax"]["max-input-tokens"] == 256000
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("max-input-tokens", "openai") is False

    def test_set_reasoning_level_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("provider=alibaba")
        gc.set_config_from_cli("reasoning-level=xhigh")
        gc.set_config_from_cli("reasoning-level=low", "openai")
        # Each provider has its own reasoning-level
        assert gc.load_reasoning_level("alibaba") == "xhigh"
        assert gc.load_reasoning_level("openai") == "low"
        # Verify storage structure
        config = _read_config(config_path)
        assert config["providers"]["alibaba"]["reasoning-level"] == "xhigh"
        assert config["providers"]["openai"]["reasoning-level"] == "low"
        # Provider-scoped set/get round-trips through the CLI helpers.
        assert gc.get_config_from_cli("reasoning-level", "alibaba") == "xhigh"

    def test_set_reasoning_level_without_provider_errors(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ProviderRequiredError):
            gc.set_config_from_cli("reasoning-level=medium")
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_load_reasoning_level_unknown_provider_returns_none(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("reasoning-level=medium", "alibaba")
        # No provider configured and unknown provider -> None
        assert gc.load_reasoning_level("unknown") is None
        assert gc.load_reasoning_level() is None

    def test_unset_reasoning_level_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("reasoning-level=xhigh", "alibaba")
        gc.set_config_from_cli("reasoning-level=low", "openai")
        assert gc.unset_config_key_from_cli("reasoning-level", "alibaba") is True
        config = _read_config(config_path)
        assert "alibaba" not in config.get("providers", {})
        assert config["providers"]["openai"]["reasoning-level"] == "low"
        # Removing again returns False (already gone)
        assert gc.unset_config_key_from_cli("reasoning-level", "alibaba") is False

    def test_load_max_output_tokens_legacy_key_fallback(monkeypatch, tmp_path):
        """Legacy context-window-size / context_window_size keys are still read."""
        config_path = _use_temp_config(monkeypatch, tmp_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "providers": {
                        "openai": {"context-window-size": 65536},
                        "minimax": {"context_window_size": 4096},
                    }
                }
            )
        )
        assert gc.load_max_output_tokens("openai") == 65536
        assert gc.load_max_output_tokens("minimax") == 4096

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

    # ---- API type (Responses / Completions) ------------------------------

    def test_api_type_config_key_helper():
        assert gc.api_type_config_key("openai") == "openai.api-type"
        assert gc.api_type_config_key("  OpenAI ") == "openai.api-type"

    def test_set_api_type_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("api-type=Responses", "openai")
        gc.set_config_from_cli("api-type=Completions", "minimax")
        assert gc.load_api_type("openai") == "Responses"
        assert gc.load_api_type("minimax") == "Completions"
        config = _read_config(config_path)
        assert config["providers"]["openai"]["api-type"] == "Responses"
        assert config["providers"]["minimax"]["api-type"] == "Completions"

    def test_set_api_type_normalizes_case(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        # Lowercase values (as in `--set api-type=completions`) are normalized
        # to the canonical casing when stored.
        key, value = gc.set_config_from_cli("api-type=completions", "openai")
        assert key == "openai.api-type"
        assert value == "Completions"
        gc.set_config_from_cli("api-type=responses", "minimax")
        gc.set_config_from_cli("api-type=RESPONSES", "deepseek")
        config = _read_config(config_path)
        assert config["providers"]["openai"]["api-type"] == "Completions"
        assert config["providers"]["minimax"]["api-type"] == "Responses"
        assert config["providers"]["deepseek"]["api-type"] == "Responses"
        assert gc.load_api_type("openai") == "Completions"
        assert gc.load_api_type("minimax") == "Responses"

    def test_set_api_type_rejects_unknown_values(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ValueError) as exc:
            gc.set_config_from_cli("api-type=bogus", "openai")
        assert "Unsupported API type" in str(exc.value)
        assert "Responses" in str(exc.value)
        assert "Completions" in str(exc.value)
        assert "Anthropic" in str(exc.value)
        # Nothing should have been written
        assert _read_config(config_path) == {}

    @requires_no_anthropic
    def test_set_api_type_anthropic_aborts_without_package(monkeypatch, tmp_path):
        """Setting the native Anthropic SDK API type without the optional
        `anthropic` package aborts the change (nothing is written) with a
        message naming the package."""
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ValueError) as exc:
            gc.set_config_from_cli("api-type=Anthropic", "anthropic")
        message = str(exc.value)
        assert "Anthropic" in message
        assert "anthropic" in message
        assert "pip install anthropic" in message
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_set_api_type_dashscope_aborts_without_package(monkeypatch, tmp_path):
        """Setting the native DashScope SDK API type without the optional
        `dashscope` package aborts the change (nothing is written) with a
        message naming the package."""
        import importlib.util

        # Simulate a test environment without the optional package so the
        # guard is exercised even when `dashscope` is installed locally.
        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ValueError) as exc:
            gc.set_config_from_cli("api-type=dashscope", "alibaba")
        message = str(exc.value)
        assert "DashScope" in message
        assert "dashscope" in message
        assert "pip install dashscope" in message
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_normalize_api_type_accepts_native_sdk_types():
        assert gc.normalize_api_type("anthropic") == "Anthropic"
        assert gc.normalize_api_type("ANTHROPIC") == "Anthropic"
        assert gc.normalize_api_type("Anthropic") == "Anthropic"
        # "DashScope" keeps its canonical casing (capitalize() would mangle it
        # into "Dashscope", so matching is case-insensitive over the known set).
        assert gc.normalize_api_type("dashscope") == "DashScope"
        assert gc.normalize_api_type("DASHSCOPE") == "DashScope"
        assert gc.normalize_api_type("DashScope") == "DashScope"

    def test_load_api_type_unknown_provider_returns_none(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("api-type=Responses", "openai")
        assert gc.load_api_type("unknown") is None
        assert gc.load_api_type() is None

    def test_unset_api_type_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("api-type=Responses", "openai")
        assert gc.unset_config_key_from_cli("api-type", "openai") is True
        assert "openai" not in config_path.read_text()
        assert gc.unset_config_key_from_cli("api-type", "openai") is False

    def test_resolve_api_type_defaults_to_provider_first_supported(
        monkeypatch, tmp_path
    ):
        _use_temp_config(monkeypatch, tmp_path)
        # OpenAI's supported_api_types is ["Responses", "Completions"], so the
        # default (first entry) is the Responses API.
        assert gc.resolve_api_type(None, "openai") == "Responses"
        # DeepSeek now ships Responses first too, so it resolves to Responses.
        assert gc.resolve_api_type(None, "deepseek") == "Responses"
        # Completions-first providers resolve to Completions.
        assert gc.resolve_api_type(None, "alibaba") == "Completions"
        # Explicit CLI flag wins over the provider default.
        assert gc.resolve_api_type("Completions", "openai") == "Completions"
        assert gc.resolve_api_type("Responses", "deepseek") == "Responses"
        # Case is normalized.
        assert gc.resolve_api_type("responses", "deepseek") == "Responses"
        # The native DashScope SDK type resolves (canonical casing) for alibaba.
        assert gc.resolve_api_type("dashscope", "alibaba") == "DashScope"

    def test_resolve_api_type_from_config(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        # No config: provider default applies (Responses for OpenAI).
        assert gc.resolve_api_type(None, "openai") == "Responses"
        # A per-provider config override wins over the built-in default.
        gc.set_config_from_cli("api-type=Completions", "openai")
        assert gc.resolve_api_type(None, "openai") == "Completions"
        # ... and the CLI flag still wins over the config value.
        assert gc.resolve_api_type("Responses", "openai") == "Responses"

    def test_resolve_api_type_rejects_unknown_values():
        with pytest.raises(ValueError) as exc:
            gc.resolve_api_type("Bogus", "openai")
        assert "Unsupported API type" in str(exc.value)
        assert "Responses" in str(exc.value)
        assert "Completions" in str(exc.value)
        assert "Anthropic" in str(exc.value)

    def test_resolve_api_type_unknown_provider_falls_back_to_completions():
        # An unknown provider has no supported_api_types entry, so the safe
        # Completions default applies.
        assert gc.resolve_api_type(None, "bogus") == "Completions"

    # ---- Responses-in-server (per-provider override) --------------------

    def test_responses_in_server_config_key_helper():
        assert (
            gc.responses_in_server_config_key("openai") == "openai.responses-in-server"
        )
        assert (
            gc.responses_in_server_config_key("  OpenAI ")
            == "openai.responses-in-server"
        )

    def test_set_responses_in_server_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("responses-in-server=true", "openai")
        gc.set_config_from_cli("responses-in-server=false", "deepseek")
        assert gc.load_responses_in_server_from_config("openai") is True
        assert gc.load_responses_in_server_from_config("deepseek") is False
        config = _read_config(config_path)
        assert config["providers"]["openai"]["responses-in-server"] is True
        assert config["providers"]["deepseek"]["responses-in-server"] is False

    def test_set_responses_in_server_normalizes_bool_forms(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        # 1/0 and on/off (in any case) are normalized to real booleans.
        key, value = gc.set_config_from_cli("responses-in-server=1", "openai")
        assert key == "openai.responses-in-server"
        assert value is True
        gc.set_config_from_cli("responses-in-server=OFF", "deepseek")
        config = _read_config(config_path)
        assert config["providers"]["openai"]["responses-in-server"] is True
        assert config["providers"]["deepseek"]["responses-in-server"] is False

    def test_set_responses_in_server_rejects_unknown_values(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        with pytest.raises(ValueError) as exc:
            gc.set_config_from_cli("responses-in-server=maybe", "openai")
        assert "boolean" in str(exc.value)
        # Nothing should have been written
        assert _read_config(config_path) == {}

    def test_load_responses_in_server_defaults_to_none(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        assert gc.load_responses_in_server_from_config("openai") is None
        assert gc.load_responses_in_server_from_config() is None

    def test_unset_responses_in_server_per_provider(monkeypatch, tmp_path):
        config_path = _use_temp_config(monkeypatch, tmp_path)
        gc.set_config_from_cli("responses-in-server=true", "openai")
        assert gc.unset_config_key_from_cli("responses-in-server", "openai") is True
        assert "openai" not in config_path.read_text()
        assert gc.unset_config_key_from_cli("responses-in-server", "openai") is False

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
