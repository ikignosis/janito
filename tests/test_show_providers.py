"""
Tests for ``janito --show-providers``.

The command lists every supported provider from the provider config registry
(read via ``janito.providers.get_provider_config``; with its
built-in default model, API types, endpoint, token limits, thinking/reasoning
defaults and API-key status) followed by the registered provider variants
(``<provider>-<word>``, marked with their base provider). The configured
default provider is flagged ``[active]``.

These tests cover:
1. the CLI parser accepts ``--show-providers``;
2. all built-in providers are listed with their key fields;
3. registered variants are appended with the variant/base-provider markers;
4. per-provider configured overrides (model, endpoint) and masked API keys;
5. the ``[active]`` marker for the configured default provider.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_cli as cc
import janito.config_dir as config_dir_mod
import janito.config_store as cs
import janito.config_variants as cv
from janito.auth_config import set_api_key
from janito.cli.handlers.providers import handle_show_providers
from janito.provider_validation import list_supported_providers


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _run(monkeypatch, tmp_path, capsys):
    """Run handle_show_providers against a temp config dir and capture output."""
    _use_temp_config(monkeypatch, tmp_path)
    rc = handle_show_providers(SimpleNamespace())
    return rc, capsys.readouterr().out


# ---------------------------------------------------------------------------
# 1. Parser
# ---------------------------------------------------------------------------


def test_parser_accepts_show_providers():
    from janito.cli.parser import create_parser

    args = create_parser().parse_args(["--show-providers"])
    assert args.show_providers is True


# ---------------------------------------------------------------------------
# 2. Built-in providers
# ---------------------------------------------------------------------------


def test_lists_all_builtin_providers(monkeypatch, tmp_path, capsys):
    rc, out = _run(monkeypatch, tmp_path, capsys)

    assert rc == 0
    assert f"Supported Providers ({len(list_supported_providers())})" in out
    for name in list_supported_providers():
        assert name in out

    # Spot-check fields of a built-in provider.
    assert "gpt-5.6-luna (default)" in out  # openai
    assert "Responses (default), Completions" in out  # openai
    assert "enabled" in out  # deepseek / alibaba


def test_custom_provider_shows_endpoint_hint(monkeypatch, tmp_path, capsys):
    _, out = _run(monkeypatch, tmp_path, capsys)
    assert "custom" in out
    assert "custom (set endpoint with --set" in out
    assert "endpoint=URL)" in out


# ---------------------------------------------------------------------------
# 3. Variants
# ---------------------------------------------------------------------------


def test_lists_registered_variants(monkeypatch, tmp_path, capsys):
    _use_temp_config(monkeypatch, tmp_path)
    cv.create_variant("alibaba-tokenplan")
    cv.create_variant("custom-local")

    rc, out = _run(monkeypatch, tmp_path, capsys)

    assert rc == 0
    assert "alibaba-tokenplan (variant of alibaba)" in out
    assert "custom-local (variant of custom)" in out

    # The variant inherits the base provider's built-in defaults.
    assert "qwen3.8-max (default)" in out  # alibaba default
    assert "Completions (default), Responses, DashScope" in out


# ---------------------------------------------------------------------------
# 4. Configured overrides and API keys
# ---------------------------------------------------------------------------


def test_shows_configured_overrides_and_masked_key(monkeypatch, tmp_path, capsys):
    _use_temp_config(monkeypatch, tmp_path)
    cv.create_variant("alibaba-tokenplan")
    cc.set_config_from_cli("model=qwen-plus", "alibaba-tokenplan")
    cc.set_config_from_cli(
        "endpoint=https://variant.example.com/v1", "alibaba-tokenplan"
    )
    set_api_key(
        "alibaba-tokenplan",
        "sk-abcdef1234567890wxyz",  # pragma: allowlist secret
    )

    _, out = _run(monkeypatch, tmp_path, capsys)

    assert "qwen-plus (configured; default qwen3.8-max)" in out
    assert "https://variant.example.com/v1" in out
    assert "sk-abc.............wxyz (set)" in out


def test_api_key_hidden_for_unset_providers(monkeypatch, tmp_path, capsys):
    _, out = _run(monkeypatch, tmp_path, capsys)
    assert "(not set)" in out


# ---------------------------------------------------------------------------
# 5. Active marker
# ---------------------------------------------------------------------------


def test_active_marker_follows_configured_provider(monkeypatch, tmp_path, capsys):
    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("provider", "deepseek")

    _, out = _run(monkeypatch, tmp_path, capsys)

    assert "openai" in out
    assert "deepseek [active]" in out


def test_active_marker_for_variant(monkeypatch, tmp_path, capsys):
    _use_temp_config(monkeypatch, tmp_path)
    cv.create_variant("alibaba-tokenplan")
    cs.set_config_value("provider", "alibaba-tokenplan")

    _, out = _run(monkeypatch, tmp_path, capsys)

    assert "alibaba-tokenplan (variant of alibaba) [active]" in out


# ---------------------------------------------------------------------------
# 6. Config file path shown
# ---------------------------------------------------------------------------


def test_shows_config_file_path(monkeypatch, tmp_path, capsys):
    config_path = _use_temp_config(monkeypatch, tmp_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({}, f)

    _, out = _run(monkeypatch, tmp_path, capsys)

    assert f"Config file:  {config_path}" in out
