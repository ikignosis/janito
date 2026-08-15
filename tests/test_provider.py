"""
Tests for the Provider / ProviderRegistry classes (janito.provider_models /
janito.provider_registry).

Covers typed accessors, case-insensitive lookup, the whitespace distinction
between ``get`` (no strip, mirrors get_provider_config) and ``canonical_name``
(strips), runtime mutation of ``janito.providers._PROVIDER_CONFIGS``, and
validation errors.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.provider_accessors as pa
import janito.provider_validation as pv
import janito.providers as pvd
from janito.provider_models import Provider
from janito.provider_registry import ProviderRegistry

if pytest is not None:

    def test_provider_accessors():
        p = Provider("alibaba")
        assert p.name == "alibaba"
        assert p.default_model() == "qwen3.8-max"
        assert p.reasoning_level() == "xhigh"
        assert p.default_thinking() is True
        assert p.supported_api_types() == ["Completions", "Responses", "DashScope"]
        assert p.default_api_type() == "Completions"
        assert p.is_custom is False

    def test_provider_custom():
        p = Provider("custom")
        assert p.is_custom is True
        assert p.default_model() is None
        assert p.max_input_tokens() is None

    def test_provider_unknown_raises():
        with pytest.raises(ValueError):
            Provider("bogus")

    def test_provider_endpoint_for():
        p = Provider("anthropic")
        assert p.endpoint_for("Completions") == "https://api.anthropic.com/v1/"
        assert p.endpoint_for("Anthropic") == "https://api.anthropic.com"
        # Multi-entry map: an absent API type falls back to the built-in endpoint.
        assert p.endpoint_for("Responses") == "https://api.anthropic.com/v1/"

    def test_registry_get_case_insensitive():
        reg = ProviderRegistry()
        assert reg.get("openai").name == "openai"
        assert reg.get("OpenAI").name == "openai"
        # get() does NOT strip whitespace (mirrors get_provider_config).
        assert reg.get("  MiniMax ") is None
        assert reg.get("bogus") is None
        assert reg.get("") is None

    def test_registry_canonical_name_strips():
        reg = ProviderRegistry()
        assert reg.canonical_name("  MiniMax ") == "minimax"
        assert reg.canonical_name("  ") is None
        assert reg.canonical_name(None) is None

    def test_registry_require():
        reg = ProviderRegistry()
        assert reg.require("OpenAI").name == "openai"
        with pytest.raises(ValueError) as exc:
            reg.require("bogus")
        assert "Supported providers" in str(exc.value)
        for name in pv.list_supported_providers():
            assert name in str(exc.value)

    def test_registry_names():
        reg = ProviderRegistry()
        assert reg.names() == pv.list_supported_providers()

    def test_registry_reflects_runtime_mutations():
        """The registry holds a reference (never a copy) to _PROVIDER_CONFIGS,
        so injecting/restoring a provider is visible to every lookup."""
        reg = ProviderRegistry()
        original = dict(pvd._PROVIDER_CONFIGS)
        pvd._PROVIDER_CONFIGS["fake-provider"] = {
            "default_model": "fake-model",
            "endpoint": None,
            "models": {
                "fake-model": {
                    "supported_api_types": ["Completions"],
                    "max_input_tokens": None,
                    "max_output_tokens": None,
                }
            },
        }
        try:
            assert reg.get("fake-provider") is not None
            assert reg.get("fake-provider").default_model() == "fake-model"
            assert reg.canonical_name("Fake-Provider") == "fake-provider"
            assert "fake-provider" in reg.names()
        finally:
            pvd._PROVIDER_CONFIGS.clear()
            pvd._PROVIDER_CONFIGS.update(original)
        assert reg.get("fake-provider") is None

    def test_registry_requires_reference():
        reg = ProviderRegistry()
        assert reg.requires is pvd.REQUIRES_BY_API_TYPE

    def test_module_functions_agree_with_registry():
        """The module-level accessors behave identically to the class API."""
        reg = ProviderRegistry()
        assert pa.get_provider_config("minimax") == reg.get("minimax").info
        assert (
            pa.get_base_url_from_provider("minimax")
            == reg.get("minimax").info["endpoint"]
        )
        assert (
            pa.get_default_model_from_provider("openai")
            == reg.get("openai").default_model()
        )
        assert (
            pa.get_default_thinking_from_provider("deepseek")
            == reg.get("deepseek").default_thinking()
        )
        assert (
            pa.get_default_api_type_from_provider("anthropic")
            == reg.get("anthropic").default_api_type()
        )
        assert pv.list_supported_providers() == reg.names()
        assert pv.validate_provider_name("OpenAI") == reg.require("OpenAI").name
        assert pv.canonical_provider_name("  MiniMax ") == reg.canonical_name(
            "  MiniMax "
        )

    def test_responses_in_server_override_honored(monkeypatch, tmp_path):
        """Provider.responses_in_server() honors a model-scoped config override
        (and the module function delegates to it)."""
        import janito.config_store as gc

        monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
        gc.set_config_value("openai.models.gpt-5.6-luna.responses-in-server", False)
        assert Provider("openai").responses_in_server() is False
        assert pa.get_responses_in_server_from_provider("openai") is False

    def test_get_provider_cost():
        """get_provider_cost() delegates to the provider's cost module."""
        # DeepSeek ships a cost module: V4-Flash at $0.14 / $0.0028 (cache
        # hit) / $0.28 output per 1M tokens, formatted as NN.DDDDDD$.
        assert (
            pa.get_provider_cost(
                "deepseek", "deepseek-v4-flash", 1_000_000, 1_000_000, 0
            )
            == "0.420000$"
        )
        # Cached input tokens are billed at the cache-hit rate.
        assert (
            pa.get_provider_cost(
                "deepseek", "deepseek-v4-flash", 1_000_000, 1_000_000, 500_000
            )
            == "0.351400$"
        )
        # Case-insensitive provider lookup (V4-Pro at $0.435 / $0.87).
        assert (
            pa.get_provider_cost("DeepSeek", "deepseek-v4-pro", 1_000_000, 1_000_000, 0)
            == "1.305000$"
        )
        # Unknown models within the provider fall back to "N/A".
        assert pa.get_provider_cost("deepseek", "bogus-model", 1000, 500, 100) == "N/A"
        # Providers without a cost module fall back to "N/A".
        assert pa.get_provider_cost("openai", "gpt-5.6-luna", 1000, 500, 100) == "N/A"
        # Unknown providers fall back to "N/A".
        assert pa.get_provider_cost("bogus", "model", 1000, 500, 100) == "N/A"

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
