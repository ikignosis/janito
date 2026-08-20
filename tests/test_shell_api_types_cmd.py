"""
Tests for the shell /api_types command handler.

``/api_types`` renders a table with one row per built-in model: the
provider, the model name and the API types the model supports (from its
``supported_api_types`` entry via
:func:`janito.provider_accessors.get_supported_api_types_from_provider`),
marking the built-in default API type (its ``default_api_type`` entry, via
:func:`janito.provider_accessors.get_default_api_type_from_provider`) with
``(default)``.  Models without a built-in entry (e.g. the ``custom``
provider's) show ``(none)``.  The command must not match non-``/api_types``
input (e.g. ``/api_type``).
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_dir as config_dir_mod
from janito.provider_accessors import (
    get_default_api_type_from_provider,
    get_supported_api_types_from_provider,
)
from janito.provider_registry import _registry
from janito.provider_validation import list_supported_providers
from janito.shell import InteractiveShell
from janito.shell.cmds.registry import get_registered_commands


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _shell():
    """Build a fresh shell for testing."""
    return InteractiveShell(model="test-model", no_history=True)


def _api_types_handler():
    """Return the registered /api_types command handler."""
    return next(c for c in get_registered_commands() if c.name == "/api_types")


def test_api_types_command_is_registered():
    """The /api_types handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/api_types" in names


def test_api_types_lists_providers_and_models(monkeypatch, tmp_path, capsys):
    """``/api_types`` lists every built-in provider and its built-in models."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _api_types_handler().handle(shell, "/api_types") is True

    out = capsys.readouterr().out
    for provider in list_supported_providers():
        found = _registry.get(provider)
        for model in found.model_names():
            assert provider in out
            assert model in out


def test_api_types_column_matches_provider_accessors(monkeypatch, tmp_path, capsys):
    """The supported API types column equals the provider accessor output."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _api_types_handler().handle(shell, "/api_types") is True

    out = capsys.readouterr().out
    for provider in list_supported_providers():
        found = _registry.get(provider)
        for model in found.model_names():
            api_types = get_supported_api_types_from_provider(provider, model) or []
            default_api_type = get_default_api_type_from_provider(provider, model)
            for api_type in api_types:
                assert api_type in out
                if api_type == default_api_type:
                    assert f"{api_type} (default)" in out


def test_api_types_default_marker(monkeypatch, tmp_path, capsys):
    """The default API type of a model is marked (default)."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _api_types_handler().handle(shell, "/api_types") is True

    out = capsys.readouterr().out
    # OpenAI's default model defaults to the Responses API type.
    assert "Responses (default)" in out
    assert "Completions" in out
    # Alibaba defaults to the Responses API type.
    assert "Responses (default)" in out
    assert "Completions" in out
    assert "DashScope" in out


def test_api_types_custom_provider_has_no_rows(monkeypatch, tmp_path, capsys):
    """The custom provider has no built-in models, so no (none) row is shown."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _api_types_handler().handle(shell, "/api_types") is True

    out = capsys.readouterr().out
    assert "(none)" not in out


def test_non_api_types_input_is_not_handled(capsys):
    """``/api_type`` (singular) must not match the /api_types command."""
    shell = _shell()
    assert _api_types_handler().handle(shell, "/api_type") is False
    assert capsys.readouterr().out == ""
