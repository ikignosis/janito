"""
Tests for ``janito --list-models``.

The command lists every model config-available from the provider (set via
``--provider`` or defined in config.json): the provider's built-in models
(its provider-config ``models`` registry) plus any per-model config entries
stored under ``providers.<provider>.models`` in config.json (custom models
with model-scoped settings).  The effective current model is flagged:
``--model``, then the provider's configured model (``<provider>.model``),
then the provider's built-in default model.

These tests cover:
1. the CLI parser accepts ``--list-models``;
2. built-in models are listed for a ``--provider`` selection;
3. the provider is read from config.json when ``--provider`` is omitted;
4. it falls back to ``openai`` when no provider is configured;
5. configured per-model entries (custom models) are included;
6. the ``(default)`` / ``(configured)`` / ``(current)`` markers;
7. a ``--model`` override is shown even when not in the registry;
8. the config file path is shown.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_dir as config_dir_mod
import janito.config_store as cs
from janito.cli.handlers.models import handle_list_models


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _run(monkeypatch, tmp_path, capsys, **kwargs):
    """Run handle_list_models against a temp config dir and capture output."""
    _use_temp_config(monkeypatch, tmp_path)
    rc = handle_list_models(SimpleNamespace(**kwargs))
    return rc, capsys.readouterr().out


# ---------------------------------------------------------------------------
# 1. Parser
# ---------------------------------------------------------------------------


def test_parser_accepts_list_models():
    from janito.cli.parser import create_parser

    args = create_parser().parse_args(["--list-models"])
    assert args.list_models is True


def test_parser_accepts_list_models_with_provider():
    from janito.cli.parser import create_parser

    args = create_parser().parse_args(["--list-models", "--provider", "deepseek"])
    assert args.list_models is True
    assert args.provider == "deepseek"


# ---------------------------------------------------------------------------
# 2. Built-in models from --provider
# ---------------------------------------------------------------------------


def test_lists_builtin_models_for_cli_provider(monkeypatch, tmp_path, capsys):
    rc, out = _run(monkeypatch, tmp_path, capsys, provider="openai")

    assert rc == 0
    assert "Models available from provider 'openai' (CLI argument):" in out
    assert "gpt-5.6-luna" in out  # openai's built-in model
    assert "gpt-5.6-luna (default, current)" in out


def test_lists_all_builtin_models(monkeypatch, tmp_path, capsys):
    """Every built-in model of the provider is listed."""
    _, out = _run(monkeypatch, tmp_path, capsys, provider="deepseek")

    assert "deepseek-v4-flash" in out
    assert "deepseek-v4-pro" in out


# ---------------------------------------------------------------------------
# 3. Provider from config.json
# ---------------------------------------------------------------------------


def test_provider_read_from_config_json(monkeypatch, tmp_path, capsys):
    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("provider", "deepseek")

    rc, out = _run(monkeypatch, tmp_path, capsys)

    assert rc == 0
    assert "Models available from provider 'deepseek' (config.json):" in out
    assert "deepseek-v4-flash" in out


def test_falls_back_to_openai(monkeypatch, tmp_path, capsys):
    """With no --provider and no configured provider, openai is used."""
    rc, out = _run(monkeypatch, tmp_path, capsys)

    assert rc == 0
    assert "Models available from provider 'openai' (fallback):" in out
    assert "gpt-5.6-luna" in out


# ---------------------------------------------------------------------------
# 4. Configured per-model entries (custom models)
# ---------------------------------------------------------------------------


def test_lists_configured_per_model_entries(monkeypatch, tmp_path, capsys):
    """A custom model with model-scoped settings in config.json is listed."""
    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("openai.models.gpt-future.max-output-tokens", 1000)

    _, out = _run(monkeypatch, tmp_path, capsys, provider="openai")

    assert "gpt-5.6-luna" in out
    assert "gpt-future" in out


def test_configured_model_is_marked(monkeypatch, tmp_path, capsys):
    """The provider's configured model (<provider>.model) is flagged."""
    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("openai.model", "gpt-future")

    _, out = _run(monkeypatch, tmp_path, capsys, provider="openai")

    assert "gpt-future (configured, current)" in out
    assert "gpt-5.6-luna (default)" in out


# ---------------------------------------------------------------------------
# 5. Markers
# ---------------------------------------------------------------------------


def test_default_model_marked(monkeypatch, tmp_path, capsys):
    _, out = _run(monkeypatch, tmp_path, capsys, provider="openai")
    assert "gpt-5.6-luna (default, current)" in out


def test_model_override_is_current(monkeypatch, tmp_path, capsys):
    """--model marks the effective current model even outside the registry."""
    _, out = _run(
        monkeypatch, tmp_path, capsys, provider="openai", model="gpt-custom-name"
    )

    assert "gpt-custom-name (current)" in out
    assert "gpt-5.6-luna (default)" in out


# ---------------------------------------------------------------------------
# 6. Config file path
# ---------------------------------------------------------------------------


def test_shows_config_file_path(monkeypatch, tmp_path, capsys):
    config_path = _use_temp_config(monkeypatch, tmp_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    _, out = _run(monkeypatch, tmp_path, capsys, provider="openai")

    assert f"Config file:  {config_path}" in out


# ---------------------------------------------------------------------------
# 7. Provider without built-in models
# ---------------------------------------------------------------------------


def test_custom_provider_without_models_shows_hint(monkeypatch, tmp_path, capsys):
    """The custom provider has no built-in models; a hint is printed."""
    rc, out = _run(monkeypatch, tmp_path, capsys, provider="custom")

    assert rc == 0
    assert "Models available from provider 'custom' (CLI argument):" in out
    assert "(none - set a model with: janito --set model=NAME)" in out
