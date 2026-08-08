"""
Tests for provider name validation.

Whenever ``--provider <name>`` is used, the CLI must verify that the provider
is supported (i.e. it maps to an entry in the provider -> base URL mapping).
These tests cover the helper functions and the end-to-end CLI behaviour.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
from janito.provider_config import (
    PROVIDER_INFO,
    REQUIRES_BY_API_TYPE,
    canonical_provider_name,
    ensure_api_type_available,
    get_all_api_types,
    get_base_url_from_provider,
    get_default_api_type_from_provider,
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_endpoint_by_api_type,
    get_endpoint_for_api_type,
    get_provider_info,
    get_required_package_for_api_type,
    get_responses_in_server_from_provider,
    get_supported_api_types_from_provider,
    get_supported_reasoning_levels_from_provider,
    is_api_type_available,
    is_supported_provider,
    list_supported_providers,
    validate_provider_name,
)

if pytest is not None:

    def test_supported_providers_map_to_info():
        # Every supported provider has a full info entry.
        providers = list_supported_providers()
        assert "openai" in providers
        assert "custom" in providers
        for name in providers:
            assert name in PROVIDER_INFO
            info = PROVIDER_INFO[name]
            # Every entry carries the full set of keys.
            assert "model" in info
            assert "max_input_tokens" in info
            assert "max_output_tokens" in info
            assert "endpoint" in info
            assert "supported_api_types" in info
            assert info["supported_api_types"]

    def test_get_provider_info_and_base_url():
        info = get_provider_info("minimax")
        assert info is not None
        assert info["endpoint"] == "https://api.minimax.io/v1"
        # get_base_url_from_provider returns just the endpoint.
        assert get_base_url_from_provider("minimax") == "https://api.minimax.io/v1"
        # Standard OpenAI has no custom endpoint (None).
        assert get_base_url_from_provider("openai") is None
        # Case-insensitive lookups work.
        assert get_provider_info("MiniMax")["endpoint"] == "https://api.minimax.io/v1"
        # Unknown provider returns None everywhere.
        assert get_provider_info("bogus") is None
        assert get_base_url_from_provider("bogus") is None

    def test_deepseek_provider():
        info = get_provider_info("deepseek")
        assert info is not None
        assert info["model"] == "deepseek-v4-flash"
        assert info["max_input_tokens"] == 1048576  # 1M (2**20)
        assert info["max_output_tokens"] == 393216
        assert info["endpoint"] == "https://api.deepseek.com"
        # OpenAI-compatible base URL for the OpenAI-SDK API types and the
        # Anthropic-compatible base URL for the native Anthropic SDK API type.
        assert info["supported_api_types"] == ["Responses", "Completions", "Anthropic"]
        assert info["endpoint_by_api_type"] == {
            "Completions": "https://api.deepseek.com",
            "Responses": "https://api.deepseek.com",
            "Anthropic": "https://api.deepseek.com/anthropic",
        }
        # Case-insensitive lookup.
        assert get_provider_info("DeepSeek")["endpoint"] == "https://api.deepseek.com"
        assert get_base_url_from_provider("deepseek") == "https://api.deepseek.com"
        assert get_default_model_from_provider("deepseek") == "deepseek-v4-flash"
        assert get_default_max_input_tokens_from_provider("deepseek") == 1048576
        assert get_default_max_output_tokens_from_provider("deepseek") == 393216

    def test_anthropic_provider():
        info = get_provider_info("anthropic")
        assert info is not None
        assert info["model"] == "claude-sonnet-5"
        assert info["max_input_tokens"] == 200000
        assert info["max_output_tokens"] == 64000
        assert info["endpoint"] == "https://api.anthropic.com/v1/"
        # Completions (OpenAI-compatible) is the built-in default; the native
        # Anthropic SDK API type is the second supported type.
        assert info["supported_api_types"] == ["Completions", "Anthropic"]
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions URL
        # and the native Anthropic SDK base URL.
        assert info["endpoint_by_api_type"] == {
            "Completions": "https://api.anthropic.com/v1/",
            "Anthropic": "https://api.anthropic.com",
        }
        # Case-insensitive lookup.
        assert (
            get_provider_info("Anthropic")["endpoint"]
            == "https://api.anthropic.com/v1/"
        )
        assert (
            get_base_url_from_provider("anthropic") == "https://api.anthropic.com/v1/"
        )
        assert get_default_model_from_provider("anthropic") == "claude-sonnet-5"
        assert get_default_max_input_tokens_from_provider("anthropic") == 200000
        assert get_default_max_output_tokens_from_provider("anthropic") == 64000
        assert get_default_api_type_from_provider("anthropic") == "Completions"

    def test_default_model_and_max_tokens():
        # Providers expose built-in default models / max tokens.
        assert get_default_model_from_provider("openai") == "gpt-5.6-luna"
        assert get_default_model_from_provider("alibaba") == "qwen3.8-max"
        assert get_default_max_input_tokens_from_provider("openai") == 1050000
        assert get_default_max_output_tokens_from_provider("openai") == 128000
        # The "custom" provider has no built-in defaults.
        assert get_default_model_from_provider("custom") is None
        assert get_default_max_input_tokens_from_provider("custom") is None
        assert get_default_max_output_tokens_from_provider("custom") is None
        # Unknown provider returns None.
        assert get_default_model_from_provider("bogus") is None
        assert get_default_max_input_tokens_from_provider("bogus") is None
        assert get_default_max_output_tokens_from_provider("bogus") is None

    def test_default_and_supported_reasoning_levels():
        # Alibaba's default model (qwen3.8-max) declares reasoning levels.
        assert get_default_reasoning_level_from_provider("alibaba") == "xhigh"
        supported = get_supported_reasoning_levels_from_provider("alibaba")
        assert supported is not None
        assert [entry["effort"] for entry in supported] == ["low", "medium", "xhigh"]
        for entry in supported:
            assert "effort" in entry
            assert "description" in entry
        # DeepSeek's default model (deepseek-v4-flash) declares reasoning
        # levels too (low/high/max per the DeepSeek API reference).
        supported = get_supported_reasoning_levels_from_provider("deepseek")
        assert supported is not None
        assert [entry["effort"] for entry in supported] == ["low", "high", "max"]
        for entry in supported:
            assert "effort" in entry
            assert "description" in entry
        # Case-insensitive lookup works.
        assert get_default_reasoning_level_from_provider("Alibaba") == "xhigh"
        assert get_supported_reasoning_levels_from_provider("DeepSeek") is not None
        # Providers without configurable reasoning expose None.
        assert get_default_reasoning_level_from_provider("openai") is None
        assert get_supported_reasoning_levels_from_provider("openai") is None
        assert get_default_reasoning_level_from_provider("custom") is None
        # Unknown provider returns None.
        assert get_default_reasoning_level_from_provider("bogus") is None
        assert get_supported_reasoning_levels_from_provider("bogus") is None

    def test_default_thinking():
        # DeepSeek and Alibaba/Qwen reason by default.
        assert get_default_thinking_from_provider("deepseek") is True
        assert get_default_thinking_from_provider("alibaba") is True
        assert get_default_thinking_from_provider("DeepSeek") is True
        assert get_default_thinking_from_provider("Alibaba") is True
        # The provider info entries carry the flag.
        assert PROVIDER_INFO["deepseek"]["thinking"] is True
        assert PROVIDER_INFO["alibaba"]["thinking"] is True
        # Everyone else defaults to False (explicit or absent).
        for name in (
            "openai",
            "minimax",
            "xiaomi",
            "moonshot",
            "zai",
            "xai",
            "anthropic",
            "custom",
        ):
            assert get_default_thinking_from_provider(name) is False
        # Unknown provider returns False.
        assert get_default_thinking_from_provider("bogus") is False

    def test_supported_and_default_api_types():
        # OpenAI supports both APIs and defaults to the Responses API (the
        # first entry of its supported_api_types list).
        assert get_supported_api_types_from_provider("openai") == [
            "Responses",
            "Completions",
        ]
        assert get_default_api_type_from_provider("openai") == "Responses"
        assert PROVIDER_INFO["openai"]["supported_api_types"] == [
            "Responses",
            "Completions",
        ]
        # Case-insensitive lookups work.
        assert get_default_api_type_from_provider("OpenAI") == "Responses"
        # Alibaba supports both APIs but defaults to Completions: its built-in
        # default model qwen3.8-max is not yet supported by DashScope's
        # /responses endpoint, so the out-of-the-box default must use the
        # Completions API where the model works. The native DashScope SDK
        # API type is also supported.
        assert get_supported_api_types_from_provider("alibaba") == [
            "Completions",
            "Responses",
            "DashScope",
        ]
        assert get_default_api_type_from_provider("alibaba") == "Completions"
        assert PROVIDER_INFO["alibaba"]["supported_api_types"] == [
            "Completions",
            "Responses",
            "DashScope",
        ]
        # DeepSeek supports the Responses and Completions API types (Responses
        # first, the default) plus the Anthropic-compatible API (native
        # Anthropic SDK at https://api.deepseek.com/anthropic).
        assert get_supported_api_types_from_provider("deepseek") == [
            "Responses",
            "Completions",
            "Anthropic",
        ]
        assert get_default_api_type_from_provider("deepseek") == "Responses"
        # Anthropic supports Completions (the built-in default) plus the
        # native Anthropic SDK API type.
        assert get_supported_api_types_from_provider("anthropic") == [
            "Completions",
            "Anthropic",
        ]
        assert get_default_api_type_from_provider("anthropic") == "Completions"
        # Every other provider is Completions-only for now.
        for name in (
            "minimax",
            "xiaomi",
            "moonshot",
            "zai",
            "xai",
            "custom",
        ):
            assert get_supported_api_types_from_provider(name) == ["Completions"]
            assert get_default_api_type_from_provider(name) == "Completions"
        # Unknown provider returns None.
        assert get_supported_api_types_from_provider("bogus") is None
        assert get_default_api_type_from_provider("bogus") is None

    # ---- endpoint_by_api_type (per-API-type endpoints) -------------------

    def test_endpoint_by_api_type_map():
        # Only providers that declare it expose a per-API-type endpoint map.
        assert get_endpoint_by_api_type("anthropic") == {
            "Completions": "https://api.anthropic.com/v1/",
            "Anthropic": "https://api.anthropic.com",
        }
        # Alibaba maps the OpenAI-compatible types to the compatible-mode
        # gateway and the native DashScope SDK to the native API base URL.
        assert get_endpoint_by_api_type("alibaba") == {
            "Completions": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "Responses": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "DashScope": "https://dashscope-intl.aliyuncs.com/api/v1",
        }
        # DeepSeek maps the OpenAI-compatible types to api.deepseek.com and
        # the native Anthropic SDK API type to the Anthropic-compatible URL.
        assert get_endpoint_by_api_type("deepseek") == {
            "Completions": "https://api.deepseek.com",
            "Responses": "https://api.deepseek.com",
            "Anthropic": "https://api.deepseek.com/anthropic",
        }
        # Providers without the map return None (single shared endpoint).
        assert get_endpoint_by_api_type("openai") is None
        assert get_endpoint_by_api_type("minimax") is None
        # Unknown provider returns None.
        assert get_endpoint_by_api_type("bogus") is None

    def test_get_endpoint_for_api_type_multi_entry_map():
        """A multi-entry map picks the URL of the requested API type."""
        # Anthropic: the OpenAI-compatible Completions URL and the native SDK URL.
        assert (
            get_endpoint_for_api_type("anthropic", "Completions")
            == "https://api.anthropic.com/v1/"
        )
        assert (
            get_endpoint_for_api_type("anthropic", "Anthropic")
            == "https://api.anthropic.com"
        )
        # An API type absent from the map falls back to the single built-in endpoint.
        assert (
            get_endpoint_for_api_type("anthropic", "Responses")
            == "https://api.anthropic.com/v1/"
        )
        # Without an API type the single built-in endpoint applies.
        assert get_endpoint_for_api_type("anthropic") == "https://api.anthropic.com/v1/"
        # Alibaba: the OpenAI-compatible types keep the compatible-mode URL
        # and the native DashScope SDK type uses the native API base URL.
        assert (
            get_endpoint_for_api_type("alibaba", "Completions")
            == "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
        )
        assert (
            get_endpoint_for_api_type("alibaba", "Responses")
            == "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
        )
        assert (
            get_endpoint_for_api_type("alibaba", "DashScope")
            == "https://dashscope-intl.aliyuncs.com/api/v1"
        )
        # Without an API type the provider's single built-in endpoint applies.
        assert (
            get_endpoint_for_api_type("alibaba")
            == "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
        )
        # DeepSeek: the OpenAI-compatible types share api.deepseek.com and the
        # native Anthropic SDK type uses the Anthropic-compatible base URL.
        assert (
            get_endpoint_for_api_type("deepseek", "Responses")
            == "https://api.deepseek.com"
        )
        assert (
            get_endpoint_for_api_type("deepseek", "Completions")
            == "https://api.deepseek.com"
        )
        assert (
            get_endpoint_for_api_type("deepseek", "Anthropic")
            == "https://api.deepseek.com/anthropic"
        )
        # Without an API type the single built-in endpoint applies.
        assert get_endpoint_for_api_type("deepseek") == "https://api.deepseek.com"

    def test_get_endpoint_for_api_type_single_entry_fallback():
        """A single-entry endpoint_by_api_type dict is the default for ANY
        API type (the issue's requirement), unless a config endpoint is set."""
        import janito.provider_config as pc

        # Inject a fake provider with a single-entry map to pin the rule.
        fake = {
            "model": "fake-model",
            "supported_api_types": ["Completions", "Anthropic"],
            "endpoint": "https://fallback.example/v1",
            "endpoint_by_api_type": {"Anthropic": "https://native.example"},
        }
        original = dict(pc.PROVIDER_INFO)
        pc.PROVIDER_INFO["fake-provider"] = fake
        try:
            # The single entry is used for any API type...
            assert (
                pc.get_endpoint_for_api_type("fake-provider", "Anthropic")
                == "https://native.example"
            )
            assert (
                pc.get_endpoint_for_api_type("fake-provider", "Completions")
                == "https://native.example"
            )
            assert (
                pc.get_endpoint_for_api_type("fake-provider", "Responses")
                == "https://native.example"
            )
            assert (
                pc.get_endpoint_for_api_type("fake-provider")
                == "https://native.example"
            )
        finally:
            pc.PROVIDER_INFO.clear()
            pc.PROVIDER_INFO.update(original)

    def test_get_endpoint_for_api_type_no_map_falls_back_to_endpoint():
        """Providers without the map keep their single built-in endpoint."""
        assert get_endpoint_for_api_type("openai") is None
        assert get_endpoint_for_api_type("openai", "Responses") is None
        assert (
            get_endpoint_for_api_type("minimax", "Completions")
            == "https://api.minimax.io/v1"
        )
        # Unknown provider returns None.
        assert get_endpoint_for_api_type("bogus", "Completions") is None

    # ---- REQUIRES_BY_API_TYPE (optional packages per API type) -----------

    def test_requires_by_api_type_structure():
        # The native Anthropic SDK API type requires the `anthropic` package
        # and the native DashScope SDK API type requires the `dashscope`
        # package.
        assert REQUIRES_BY_API_TYPE == {
            "Anthropic": "anthropic",
            "DashScope": "dashscope",
        }
        assert get_required_package_for_api_type("Anthropic") == "anthropic"
        assert get_required_package_for_api_type("anthropic") == "anthropic"
        assert get_required_package_for_api_type("DashScope") == "dashscope"
        assert get_required_package_for_api_type("dashscope") == "dashscope"
        # The OpenAI-SDK API types have no optional-package requirement.
        assert get_required_package_for_api_type("Responses") is None
        assert get_required_package_for_api_type("Completions") is None
        # Unknown API types have no requirement either.
        assert get_required_package_for_api_type("Bogus") is None
        assert get_required_package_for_api_type("") is None
        assert get_required_package_for_api_type(None) is None

    def test_get_all_api_types_includes_native_sdk_types():
        types = get_all_api_types()
        assert "Responses" in types
        assert "Completions" in types
        assert "Anthropic" in types
        assert "DashScope" in types

    def test_is_api_type_available(monkeypatch):
        # The OpenAI-SDK types are always available (hard dependency).
        assert is_api_type_available("Responses") is True
        assert is_api_type_available("Completions") is True
        # The native-SDK API types require optional packages; simulate a test
        # environment where neither is installed so the assertions hold even
        # when the packages are present on the machine running the suite.
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        assert is_api_type_available("Anthropic") is False
        assert is_api_type_available("DashScope") is False

    def test_ensure_api_type_available_aborts_when_package_missing(monkeypatch):
        """Setting the Anthropic API type without the `anthropic` package
        raises an actionable ValueError (the change is aborted)."""
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        with pytest.raises(ValueError) as exc:
            ensure_api_type_available("Anthropic")
        message = str(exc.value)
        assert "Anthropic" in message
        assert "anthropic" in message
        assert "pip install anthropic" in message

        # Same for the native DashScope SDK API type.
        with pytest.raises(ValueError) as exc:
            ensure_api_type_available("DashScope")
        message = str(exc.value)
        assert "DashScope" in message
        assert "dashscope" in message
        assert "pip install dashscope" in message

    def test_ensure_api_type_available_noop_without_requirement():
        # No requirement -> no error.
        ensure_api_type_available("Responses")
        ensure_api_type_available("Completions")
        ensure_api_type_available("Bogus")

    def test_responses_in_server_flag():
        """Providers whose /responses endpoint keeps server-side state chain
        with previous_response_id; stateless endpoints (DeepSeek) do not."""
        # OpenAI keeps the conversation server-side.
        assert get_responses_in_server_from_provider("openai") is True
        assert PROVIDER_INFO["openai"]["responses_in_server"] is True
        # DeepSeek's /responses endpoint is stateless.
        assert get_responses_in_server_from_provider("deepseek") is False
        assert PROVIDER_INFO["deepseek"]["responses_in_server"] is False
        # Case-insensitive lookups work.
        assert get_responses_in_server_from_provider("DeepSeek") is False
        # Providers that do not declare the flag default to True (the
        # Responses API design).
        assert get_responses_in_server_from_provider("minimax") is True
        # Unknown provider defaults to True.
        assert get_responses_in_server_from_provider("bogus") is True

    def test_responses_in_server_flag_honors_config_override(monkeypatch, tmp_path):
        """A per-provider responses-in-server override in config.json wins
        over the built-in default (e.g. set from the web Settings drawer's
        Advanced section or ``--set responses-in-server=...``)."""
        import janito.general_config as gc

        monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)

        # OpenAI's built-in default is True; force it off via config.
        gc.set_config_value("openai.responses-in-server", False)
        assert get_responses_in_server_from_provider("openai") is False

        # Clearing the override falls back to the built-in default.
        gc.unset_config_value("openai.responses-in-server")
        assert get_responses_in_server_from_provider("openai") is True

        # DeepSeek's built-in default is False; force it on via config.
        gc.set_config_value("deepseek.responses-in-server", True)
        assert get_responses_in_server_from_provider("deepseek") is True

        # Unknown providers still default to True regardless of config.
        assert get_responses_in_server_from_provider("bogus") is True

    def test_canonical_provider_name_exact_and_case_insensitive():
        assert canonical_provider_name("openai") == "openai"
        assert canonical_provider_name("OpenAI") == "openai"
        assert canonical_provider_name("  MiniMax ") == "minimax"
        assert canonical_provider_name("XAI") == "xai"

    def test_canonical_provider_name_unknown_returns_none():
        assert canonical_provider_name("bogus") is None
        assert canonical_provider_name("") is None
        assert canonical_provider_name("   ") is None
        assert canonical_provider_name(None) is None

    def test_is_supported_provider():
        assert is_supported_provider("openai")
        assert is_supported_provider("Custom")
        assert is_supported_provider("alibaba")
        assert not is_supported_provider("does-not-exist")
        assert not is_supported_provider("")

    def test_validate_provider_name_returns_canonical():
        assert validate_provider_name("OpenAI") == "openai"
        assert validate_provider_name("xai") == "xai"

    def test_validate_provider_name_raises_for_unknown():
        with pytest.raises(ValueError) as exc:
            validate_provider_name("bogus")
        message = str(exc.value)
        assert "bogus" in message
        assert "Supported providers" in message
        # The message enumerates the supported providers.
        for name in list_supported_providers():
            assert name in message

    # ---- End-to-end CLI behaviour --------------------------------------

    def _run_main(monkeypatch, tmp_path, argv):
        """Run janito.__main__.main() with the given argv and a temp config dir.

        Returns the exit code produced by main(). The config dir global is
        restored automatically by monkeypatch on teardown.
        """
        from janito.__main__ import main

        monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
        monkeypatch.setattr(sys, "argv", ["janito", "-c", str(tmp_path), *argv])
        return main()

    def test_cli_rejects_unknown_provider(monkeypatch, tmp_path):
        rc = _run_main(
            monkeypatch,
            tmp_path,
            ["--provider", "bogus", "--set", "model=gpt-4"],
        )
        assert rc == 1
        # Nothing should have been written for the bogus provider.
        config_path = tmp_path / "config.json"
        assert not config_path.exists()

    def test_cli_normalizes_provider_casing(monkeypatch, tmp_path):
        import json

        rc = _run_main(
            monkeypatch,
            tmp_path,
            ["--provider", "OpenAI", "--set", "model=gpt-4"],
        )
        assert rc == 0
        config = json.loads((tmp_path / "config.json").read_text())
        # The provider was normalized to its canonical casing ("openai").
        assert config == {"providers": {"openai": {"model": "gpt-4"}}}

    def test_web_mode_without_extra_prints_actionable_error(
        monkeypatch, tmp_path, capsys
    ):
        """`--web` without the optional [web] extra fails with the documented
        install hint instead of a defensive try/except ImportError fallback."""
        import importlib.util

        import janito.__main__ as main_mod

        # Skip runtime-config validation so we reach the web-mode branch
        # without needing an API key in the temp config dir.
        monkeypatch.setattr(main_mod, "validate_runtime_config", lambda args=None: None)
        # Simulate the optional [web] extra not being installed.
        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)

        rc = _run_main(monkeypatch, tmp_path, ["--web"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "the web UI requires optional dependencies" in err
        assert "pip install janito[web]" in err

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                try:
                    import inspect

                    params = inspect.signature(fn).parameters
                    with tempfile.TemporaryDirectory() as d:
                        if "tmp_path" in params:
                            fn(mp, Path(d))
                        else:
                            fn()
                finally:
                    mp.restore()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
