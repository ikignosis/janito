"""
Tests for the OpenRouter provider (``openrouter``).

OpenRouter is an aggregator: it proxies many models behind a single
OpenAI-compatible endpoint, so it has no single sensible default model.  Its
provider-config entry declares ``default_model: "custom"`` -- a placeholder,
not a real model name -- with a ``custom`` model entry that only carries
built-in defaults (the default API type, ``Completions``).  The user is
therefore required to supply the model explicitly (``--model`` or
``providers.openrouter.model`` in config.json); when it cannot be resolved,
runtime configuration fails with an actionable message instead of silently
sending the placeholder to the API.

These tests cover:
1. the provider entry (``default_model`` / ``models`` / endpoint);
2. ``requires_explicit_model`` (placeholder-default detection);
3. runtime resolution (``resolve_runtime_config``) without/with a model;
4. API-type resolution falling back to ``Completions``;
5. display helpers (``--show-config`` / ``--list-models``) not flagging the
   placeholder as a usable default/current model.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.config_store as cs
import janito.provider_accessors as pa
from janito.auth_config import set_api_key
from janito.cli.handlers.models import handle_list_models
from janito.cli.handlers.providers import _provider_rows
from janito.provider_models import Provider


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


# ---------------------------------------------------------------------------
# 1. Provider entry
# ---------------------------------------------------------------------------


def test_provider_registered():
    from janito.provider_validation import list_supported_providers

    assert "openrouter" in list_supported_providers()


def test_provider_config_shape():
    """default_model is the 'custom' placeholder; the models list has a
    'custom' entry whose default API type is Completions."""
    p = Provider("openrouter")
    assert p.default_model() == "custom"
    assert p.model_names() == ["custom"]
    assert p.supported_api_types() == ["Completions"]
    assert p.default_api_type() == "Completions"
    assert p.endpoint_for("Completions") == "https://openrouter.ai/api/v1"
    # Not the special "custom" provider itself (it has a real endpoint).
    assert p.is_custom is False


def test_placeholder_model_entry_carries_defaults():
    """The placeholder 'custom' model entry provides the default API type,
    so API-type resolution works before a model is configured."""
    assert pa.get_default_api_type_from_provider("openrouter", None) == "Completions"
    assert pa.get_default_model_from_provider("openrouter") == "custom"


# ---------------------------------------------------------------------------
# 2. requires_explicit_model
# ---------------------------------------------------------------------------


def test_requires_explicit_model():
    assert pa.requires_explicit_model("openrouter") is True
    # Case-insensitive lookup.
    assert pa.requires_explicit_model("OpenRouter") is True
    # Real-default providers and the custom provider do not.
    assert pa.requires_explicit_model("openai") is False
    assert pa.requires_explicit_model("custom") is False
    assert pa.requires_explicit_model("bogus") is False


# ---------------------------------------------------------------------------
# 3. Runtime resolution (resolve_runtime_config)
# ---------------------------------------------------------------------------


def test_resolve_runtime_config_requires_model(monkeypatch, tmp_path):
    """Without --model or a configured model, resolution fails with an
    actionable message instead of falling back to the placeholder."""
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)
    set_api_key("openrouter", "sk-test")  # pragma: allowlist secret

    with pytest.raises(ValueError, match="No model configured for provider"):
        resolve_runtime_config(None, "openrouter")


def test_resolve_runtime_config_cli_model(monkeypatch, tmp_path):
    """--model supplies the model explicitly."""
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)
    set_api_key("openrouter", "sk-test")  # pragma: allowlist secret

    base_url, api_key, model = resolve_runtime_config("openrouter/auto", "openrouter")
    assert base_url == "https://openrouter.ai/api/v1"
    assert api_key == "sk-test"  # pragma: allowlist secret
    assert model == "openrouter/auto"


def test_resolve_runtime_config_configured_model(monkeypatch, tmp_path):
    """A model set in config.json (providers.openrouter.model) resolves too."""
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)
    set_api_key("openrouter", "sk-test")  # pragma: allowlist secret
    cs.set_config_value("openrouter.model", "anthropic/claude-3.5-sonnet")

    _, _, model = resolve_runtime_config(None, "openrouter")
    assert model == "anthropic/claude-3.5-sonnet"


def test_resolve_api_type_defaults_to_completions(monkeypatch, tmp_path):
    """The placeholder model entry makes Completions the default API type."""
    from janito.general_config import resolve_api_type

    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("provider", "openrouter")

    assert resolve_api_type(None, "openrouter") == "Completions"


# ---------------------------------------------------------------------------
# 4. Display helpers
# ---------------------------------------------------------------------------


def test_show_providers_rows_no_placeholder_default(monkeypatch, tmp_path):
    """--show-providers does not present the placeholder as a default model."""
    _use_temp_config(monkeypatch, tmp_path)

    rows = dict(_provider_rows("openrouter"))
    assert rows["Model"] == "(not set)"

    # With a configured model, it is shown as configured (not default).
    cs.set_config_value("openrouter.model", "openrouter/auto")
    rows = dict(_provider_rows("openrouter"))
    assert rows["Model"] == "openrouter/auto (configured)"


def test_show_config_no_placeholder_model(monkeypatch, tmp_path, capsys):
    """--show-config shows the model as not configured (the placeholder is
    not treated as a usable default)."""
    from janito.cli.handlers.info import handle_show_config

    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("provider", "openrouter")

    args = SimpleNamespace(
        provider="openrouter", model=None, api_type=None, thinking=False
    )
    rc = handle_show_config(args)
    out = capsys.readouterr().out

    assert rc == 0
    assert "Model" in out and "(not configured)" in out
    assert "custom" not in out.split("Model")[1].split("\n")[0]
    # The API type still resolves through the placeholder entry.
    assert "Completions" in out


def test_list_models_no_placeholder_current(monkeypatch, tmp_path, capsys):
    """--list-models does not flag the placeholder as default/current."""
    _use_temp_config(monkeypatch, tmp_path)

    rc = handle_list_models(SimpleNamespace(provider="openrouter", model=None))
    out = capsys.readouterr().out

    assert rc == 0
    # The placeholder entry is listed (it is part of the built-in models),
    # but without the (default) / (current) markers.
    assert "custom" in out
    assert "(default" not in out
    assert "(current" not in out


def test_list_models_configured_model_current(monkeypatch, tmp_path, capsys):
    """A configured model is flagged as configured/current for openrouter."""
    _use_temp_config(monkeypatch, tmp_path)
    cs.set_config_value("openrouter.model", "openrouter/auto")

    rc = handle_list_models(SimpleNamespace(provider="openrouter", model=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert "openrouter/auto (configured, current)" in out
    assert "custom" in out
    assert "(default" not in out
