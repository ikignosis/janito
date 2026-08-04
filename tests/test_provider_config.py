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
    canonical_provider_name,
    get_base_url_from_provider,
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_provider_info,
    get_supported_reasoning_levels_from_provider,
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
            assert "default_model" in info
            assert "default_max_input_tokens" in info
            assert "default_max_output_tokens" in info
            assert "endpoint" in info

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
        assert info["default_model"] == "deepseek-v4-flash"
        assert info["default_max_input_tokens"] == 1000000
        assert info["default_max_output_tokens"] == 393216
        assert info["endpoint"] == "https://api.deepseek.com"
        # Case-insensitive lookup.
        assert get_provider_info("DeepSeek")["endpoint"] == "https://api.deepseek.com"
        assert get_base_url_from_provider("deepseek") == "https://api.deepseek.com"
        assert get_default_model_from_provider("deepseek") == "deepseek-v4-flash"
        assert get_default_max_input_tokens_from_provider("deepseek") == 1000000
        assert get_default_max_output_tokens_from_provider("deepseek") == 393216

    def test_default_model_and_max_tokens():
        # Providers expose built-in default models / max tokens.
        assert get_default_model_from_provider("openai") == "gpt-4"
        assert get_default_model_from_provider("alibaba") == "qwen3.8-max"
        assert get_default_max_input_tokens_from_provider("openai") == 128000
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
        # Case-insensitive lookup works.
        assert get_default_reasoning_level_from_provider("Alibaba") == "xhigh"
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
        assert PROVIDER_INFO["deepseek"]["default_thinking"] is True
        assert PROVIDER_INFO["alibaba"]["default_thinking"] is True
        # Everyone else defaults to False (explicit or absent).
        for name in ("openai", "minimax", "xiaomi", "moonshot", "zai", "xai", "custom"):
            assert get_default_thinking_from_provider(name) is False
        # Unknown provider returns False.
        assert get_default_thinking_from_provider("bogus") is False

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
