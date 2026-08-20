"""
Tests for provider variants (issue #47).

A provider variant is a second configuration for an already-supported
provider, named ``<provider>-<word>`` (e.g. ``alibaba-tokenplan``).  It is
registered with ``janito --create-variant <name>``, stored as a
``providers`` entry in config.json, and afterwards the name behaves like any
provider: it is accepted by ``--provider`` / ``--set provider=``, inherits
the base provider's built-in defaults, keeps its own per-variant
model/endpoint/API key, and is removed with ``janito --delete-variant``.
(The web UI lists registered variants in the provider combos but does not
create or delete them -- those operations are CLI-only.)

These tests cover:
1. variant name parsing / shape validation;
2. ``create_variant`` (registration, canonical casing, error cases);
3. ``delete_variant`` (cleanup of entry + scoped keys + auth key, guards);
4. variant-aware provider validation (``validate_provider_name`` and friends);
5. per-variant config via the CLI helpers (``--set provider=<variant>``);
6. runtime resolution (``resolve_runtime_config``) with a variant;
7. the web providers list (includes registered variants).
"""

import json
import sys
import tempfile
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_cli as cc
import janito.config_dir as config_dir_mod
import janito.config_loaders as cl
import janito.config_store as cs
import janito.config_variants as cv
import janito.provider_accessors as pa
import janito.provider_registry as pr
import janito.provider_validation as pv
from janito.auth_config import get_api_key, set_api_key


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _read_json(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Name parsing / shape validation
# ---------------------------------------------------------------------------


def test_parse_variant_name_shapes():
    assert pr.parse_variant_name("alibaba-tokenplan") == ("alibaba", "tokenplan")
    # The word may itself contain hyphens (split on the FIRST hyphen).
    assert pr.parse_variant_name("alibaba-token-plan") == ("alibaba", "token-plan")
    assert pr.parse_variant_name("custom-local") == ("custom", "local")
    # Not in <provider>-<word> form.
    assert pr.parse_variant_name("openai") is None
    assert pr.parse_variant_name("-foo") is None
    assert pr.parse_variant_name("openai-") is None
    assert pr.parse_variant_name("") is None
    assert pr.parse_variant_name(None) is None


def test_is_variant_style_name():
    assert pr.is_variant_style_name("alibaba-tokenplan") is True
    assert pr.is_variant_style_name("openai") is False


# ---------------------------------------------------------------------------
# 2. create_variant
# ---------------------------------------------------------------------------


def test_create_variant_registers_entry(monkeypatch, tmp_path):
    config_path = _use_temp_config(monkeypatch, tmp_path)

    created = cv.create_variant("alibaba-tokenplan")
    assert created == "alibaba-tokenplan"
    assert _read_json(config_path) == {"providers": {"alibaba-tokenplan": {}}}
    assert cv.is_registered_variant("alibaba-tokenplan") is True


def test_create_variant_normalizes_casing(monkeypatch, tmp_path):
    config_path = _use_temp_config(monkeypatch, tmp_path)

    created = cv.create_variant("  Alibaba-TokenPlan  ")
    assert created == "alibaba-tokenplan"
    assert _read_json(config_path) == {"providers": {"alibaba-tokenplan": {}}}
    assert cv.is_registered_variant("ALIBABA-TOKENPLAN") is True


def test_create_variant_rejects_invalid_names(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    # Empty name.
    with pytest.raises(ValueError, match="A variant name is required"):
        cv.create_variant("")
    with pytest.raises(ValueError, match="A variant name is required"):
        cv.create_variant("   ")

    # Not in <provider>-<word> form.
    for bad in ("-foo", "openai-", "openai"):
        with pytest.raises(ValueError, match="Invalid provider variant"):
            cv.create_variant(bad)

    # Unknown base provider.
    with pytest.raises(ValueError, match="Unknown base provider 'bogus'"):
        cv.create_variant("bogus-x")


def test_create_variant_rejects_duplicate(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    with pytest.raises(ValueError, match="already exists"):
        cv.create_variant("alibaba-tokenplan")
    # Case-insensitive duplicate.
    with pytest.raises(ValueError, match="already exists"):
        cv.create_variant("Alibaba-Tokenplan")


# ---------------------------------------------------------------------------
# 3. delete_variant
# ---------------------------------------------------------------------------


def test_delete_variant_removes_entry_config_and_key(monkeypatch, tmp_path):
    config_path = _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    cs.set_config_value("alibaba-tokenplan.model", "qwen-plus")
    cs.set_config_value("alibaba-tokenplan.endpoint", "https://variant.example.com/v1")
    set_api_key("alibaba-tokenplan", "sk-variant")  # pragma: allowlist secret

    removed = cv.delete_variant("alibaba-tokenplan")
    assert removed is True
    # Entry gone, scoped keys gone, auth key gone.
    assert _read_json(config_path) == {}
    assert get_api_key("alibaba-tokenplan") is None
    assert cv.is_registered_variant("alibaba-tokenplan") is False


def test_delete_variant_unregistered_returns_false(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    assert cv.delete_variant("bogus-x") is False
    assert cv.delete_variant("") is False


def test_delete_variant_refuses_default_provider(monkeypatch, tmp_path):
    config_path = _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    cs.set_config_value("provider", "alibaba-tokenplan")

    with pytest.raises(ValueError, match="default provider"):
        cv.delete_variant("alibaba-tokenplan")

    # After switching the default away, deletion succeeds.
    cs.set_config_value("provider", "openai")
    assert cv.delete_variant("alibaba-tokenplan") is True
    assert _read_json(config_path) == {"provider": "openai"}


# ---------------------------------------------------------------------------
# 4. Variant-aware provider validation
# ---------------------------------------------------------------------------


def test_validate_provider_name_accepts_registered_variant(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    assert pv.validate_provider_name("alibaba-tokenplan") == "alibaba-tokenplan"
    assert pv.validate_provider_name("ALIBABA-TOKENPLAN") == "alibaba-tokenplan"
    assert pv.is_supported_provider("alibaba-tokenplan") is True
    assert pv.canonical_provider_name("ALIBABA-TOKENPLAN") == "alibaba-tokenplan"
    assert pv.is_registered_provider_variant("alibaba-tokenplan") is True
    assert pv.list_variants() == ["alibaba-tokenplan"]


def test_validate_provider_name_rejects_unregistered_variant(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="--create-variant"):
        pv.validate_provider_name("alibaba-tokenplan")
    assert pv.is_supported_provider("alibaba-tokenplan") is False
    assert pv.is_registered_provider_variant("alibaba-tokenplan") is False


def test_variant_inherits_base_defaults(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    # The base provider's built-in defaults apply to the variant.
    assert pa.get_default_model_from_provider("alibaba-tokenplan") == "qwen3.8-max"
    assert pa.get_default_api_type_from_provider("alibaba-tokenplan") == "Responses"
    assert pa.get_default_thinking_from_provider("alibaba-tokenplan") is True
    assert pa.get_endpoint_for_api_type(
        "alibaba-tokenplan", "Completions"
    ) == pa.get_endpoint_for_api_type("alibaba", "Completions")

    # A registered variant of "custom" counts as custom.
    cv.create_variant("custom-local")
    assert pv.is_custom_provider("custom-local") is True


def test_variant_inherits_base_models_dict(monkeypatch, tmp_path):
    """A variant inherits the base provider's ``models`` dict: its model
    names, per-model token limits, reasoning and thinking defaults all come
    from the base provider's built-in entries."""
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("openai-tokenplan")
    registry = pr.ProviderRegistry()
    provider = registry.get("openai-tokenplan")
    assert provider is not None
    # Same model_names as the base provider.
    assert provider.model_names() == ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
    # Per-model accessors resolve through the inherited models dict.
    assert provider.default_model() == "gpt-5.6-luna"
    assert provider.max_input_tokens() == 1050000
    assert provider.max_output_tokens() == 128000
    assert provider.supported_api_types() == ["Responses", "Completions"]
    assert provider.default_api_type() == "Responses"
    # A per-model override lands under the VARIANT name (providers.<variant>.
    # models.<model>.<key>), not the base provider's.
    key, value = cc.set_config_from_cli("max-output-tokens=32000", "openai-tokenplan")
    assert key == "openai-tokenplan.models.gpt-5.6-luna.max-output-tokens"
    assert cl.load_max_output_tokens("openai-tokenplan") == 32000
    # The base provider is unaffected.
    assert cl.load_max_output_tokens("openai") is None


def test_variant_provider_object(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("custom-local")
    registry = pr.ProviderRegistry()
    provider = registry.get("custom-local")
    assert provider is not None
    assert provider.name == "custom-local"
    assert provider.is_variant is True
    assert provider.base_name == "custom"
    assert provider.is_custom is True
    # Same accessors as the base provider.
    assert provider.default_model() is None  # "custom" has no default model


# ---------------------------------------------------------------------------
# 5. CLI config helpers (--set provider=<variant> etc.)
# ---------------------------------------------------------------------------


def test_set_provider_to_variant(monkeypatch, tmp_path):
    config_path = _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    key, value = cc.set_config_from_cli("provider=alibaba-tokenplan")
    assert key == "provider"
    assert value == "alibaba-tokenplan"
    assert _read_json(config_path)["provider"] == "alibaba-tokenplan"


def test_set_provider_to_unregistered_variant_rejected(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="--create-variant"):
        cc.set_config_from_cli("provider=alibaba-bogus")


def test_per_variant_model_roundtrip(monkeypatch, tmp_path):
    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    key, value = cc.set_config_from_cli("model=qwen-plus", "alibaba-tokenplan")
    assert key == "alibaba-tokenplan.model"
    assert value == "qwen-plus"
    assert cl.load_model_from_config("alibaba-tokenplan") == "qwen-plus"


def test_unset_last_scoped_key_keeps_variant_registered(monkeypatch, tmp_path):
    """Unsetting the last per-variant key must NOT deregister the variant.

    The variant's registration marker is its (empty) ``providers`` entry, so
    the unset cleanup keeps the ``{}`` dict instead of pruning the entry.
    """
    config_path = _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    cs.set_config_value("alibaba-tokenplan.model", "qwen-plus")

    assert cs.unset_config_value("alibaba-tokenplan.model") is True
    assert cv.is_registered_variant("alibaba-tokenplan") is True
    assert _read_json(config_path) == {"providers": {"alibaba-tokenplan": {}}}


# ---------------------------------------------------------------------------
# 6. Runtime resolution (resolve_runtime_config)
# ---------------------------------------------------------------------------


def test_resolve_runtime_config_variant_overrides(monkeypatch, tmp_path):
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    set_api_key("alibaba-tokenplan", "sk-variant")  # pragma: allowlist secret
    cc.set_config_from_cli("model=qwen-plus", "alibaba-tokenplan")
    cc.set_config_from_cli(
        "endpoint=https://variant.example.com/v1", "alibaba-tokenplan"
    )

    base_url, api_key, model = resolve_runtime_config(None, "alibaba-tokenplan")
    assert base_url == "https://variant.example.com/v1"
    assert api_key == "sk-variant"  # pragma: allowlist secret
    assert model == "qwen-plus"


def test_resolve_runtime_config_variant_base_fallback(monkeypatch, tmp_path):
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    set_api_key("alibaba-tokenplan", "sk-variant")  # pragma: allowlist secret

    # No per-variant overrides: the base provider's defaults apply.
    base_url, api_key, model = resolve_runtime_config(None, "alibaba-tokenplan")
    assert base_url == pa.get_endpoint_for_api_type("alibaba", "Completions")
    assert api_key == "sk-variant"  # pragma: allowlist secret
    assert model == pa.get_default_model_from_provider("alibaba")


def test_resolve_runtime_config_variant_no_key_error(monkeypatch, tmp_path):
    from janito.openai_client.completions_api import resolve_runtime_config

    _use_temp_config(monkeypatch, tmp_path)

    cv.create_variant("alibaba-tokenplan")
    with pytest.raises(ValueError, match="alibaba-tokenplan"):
        resolve_runtime_config(None, "alibaba-tokenplan")


# ---------------------------------------------------------------------------
# 7. Web endpoints (require the optional web extra)
# ---------------------------------------------------------------------------

try:
    from fastapi.testclient import TestClient  # noqa: F401

    _HAS_FASTAPI = True
except ModuleNotFoundError:
    _HAS_FASTAPI = False

requires_fastapi = pytest.mark.skipif(
    not _HAS_FASTAPI, reason="fastapi (web extra) is not installed"
)


@pytest.fixture(scope="module")
def web_client():
    """A TestClient wired to a fresh Janito web app (isolated config dir)."""
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_variant_tests_")
    config_dir_mod.set_config_dir(tmp)

    from janito.web.backend.config import WebServerConfig

    prev = (WebServerConfig.provider, WebServerConfig.model)
    WebServerConfig.provider = None
    WebServerConfig.model = None

    from janito.web.backend.app import create_app

    config = WebServerConfig(web_host="127.0.0.1", web_port=0, no_web_open=True)
    app = create_app(config)
    with TestClient(app) as c:
        yield c

    config_dir_mod.set_config_dir(str(prev_dir))
    WebServerConfig.provider, WebServerConfig.model = prev


@requires_fastapi
def test_web_providers_list_includes_variant(web_client):
    cv.create_variant("alibaba-tokenplan")
    set_api_key("alibaba-tokenplan", "sk-variant")  # pragma: allowlist secret

    resp = web_client.get("/api/config/providers")
    assert resp.status_code == 200
    entries = {p["name"]: p for p in resp.json()["providers"]}

    assert "alibaba-tokenplan" in entries
    variant = entries["alibaba-tokenplan"]
    assert variant["variant"] is True
    assert variant["base_provider"] == "alibaba"
    assert variant["api_key_set"] is True
    # Inherits the base's built-in defaults.
    assert variant["default_model"] == "qwen3.8-max"
    assert variant["default_thinking"] is True

    # Base providers do not carry the variant markers.
    assert "variant" not in entries["openai"]
