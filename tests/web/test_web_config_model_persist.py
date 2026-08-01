"""Backend tests: the Settings drawer's model edit is persisted to config.json.

The Settings drawer (``janito/web/frontend/js/settings.js``) saves the model
via ``PATCH /api/config`` with the provider the field describes (the combo's
selection).  Models are stored *per provider* in ``~/.janito/config.json``
under ``providers.<name>.model`` — mirroring the CLI's ``--set model=<name>``
— so the endpoint must write the value to disk (previously it only updated
the running server in memory and the change was lost on restart) and scope it
to the right provider.

These tests pin down:

1. ``PATCH /api/config`` with ``{model, provider}`` persists the value under
   ``providers.<provider>.model`` in config.json;
2. without an explicit ``provider`` the model is applied to the provider the
   next prompt resolves to (session override, else the persisted default);
3. the change is mirrored into the running server only when it affects the
   provider currently in use;
4. an empty ``model`` clears the per-provider override;
5. an unknown ``provider`` is rejected with ``400``;
6. the frontend wiring (settings.js) sends the selected provider alongside
   the model so it lands under the correct provider.
"""

import sys
import tempfile
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import janito.auth_config as ac
import janito.config_dir as config_dir_mod
import janito.general_config as gc

# The web routes need the optional `web` extra (fastapi). Skip gracefully
# when fastapi is not installed (e.g. minimal tox envs).
try:
    import fastapi  # noqa: F401
    from fastapi.testclient import TestClient

    _HAS_FASTAPI = True
except ModuleNotFoundError:
    _HAS_FASTAPI = False

requires_fastapi = pytest.mark.skipif(
    not _HAS_FASTAPI, reason="fastapi (web extra) is not installed"
)

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


@pytest.fixture(scope="module", autouse=True)
def clean_config(request):
    """Isolate the config dir in a temp dir + reset WebServerConfig class state.

    ``WebServerConfig.provider/model`` are mutated by the PATCH endpoint
    (mirrored into the running server), so the class-level defaults are
    restored afterwards to keep other test modules unaffected.
    """
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_patch_model_tests_")
    config_dir_mod.set_config_dir(tmp)

    from janito.web.backend.config import WebServerConfig

    prev = (
        WebServerConfig.provider,
        WebServerConfig.model,
        WebServerConfig.session_provider,
    )
    WebServerConfig.provider = None
    WebServerConfig.model = None
    WebServerConfig.session_provider = None

    def restore():
        config_dir_mod.set_config_dir(str(prev_dir))
        (
            WebServerConfig.provider,
            WebServerConfig.model,
            WebServerConfig.session_provider,
        ) = prev

    request.addfinalizer(restore)


@pytest.fixture(scope="module")
def client(clean_config):
    """A TestClient wired to a fresh Janito web app (isolated config dir)."""
    from janito.web.backend.app import create_app
    from janito.web.backend.config import WebServerConfig

    config = WebServerConfig(web_host="127.0.0.1", web_port=0, no_web_open=True)
    app = create_app(config)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# PATCH /api/config — the Settings drawer Save (model persistence)
# ---------------------------------------------------------------------------


@requires_fastapi
def test_patch_model_with_provider_persists_per_provider(client):
    """{model, provider} writes providers.<provider>.model to config.json."""
    # Make sure the config.json has no stale model for the target provider.
    gc.unset_config_value("minimax.model")

    resp = client.patch(
        "/api/config", json={"model": "MiniMax-M3", "provider": "minimax"}
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["model"] == "MiniMax-M3"

    # Persisted per-provider on disk (the core of the fix).
    assert (
        gc.load_config().get("providers", {}).get("minimax", {}).get("model")
        == "MiniMax-M3"
    )
    # ...and readable through the per-provider loader too.
    assert gc.load_model_from_config("minimax") == "MiniMax-M3"


@requires_fastapi
def test_patch_model_without_provider_targets_active_provider(client):
    """Without an explicit provider, the model lands on the active one."""
    assert ac.set_api_key("openai", "sk-openai-test") is True
    assert gc.set_config_value("provider", "openai") is None
    gc.unset_config_value("openai.model")
    client.app.state.config.session_provider = None

    resp = client.patch("/api/config", json={"model": "gpt-4o"})
    assert resp.status_code == 200

    # Applied to the persisted default (openai), not any other provider.
    assert (
        gc.load_config().get("providers", {}).get("openai", {}).get("model") == "gpt-4o"
    )
    assert gc.load_model_from_config("minimax") in (None, "MiniMax-M3")


@requires_fastapi
def test_patch_model_mirrored_into_running_server_when_effective(client):
    """When the change affects the provider in use, the server model updates."""
    assert ac.set_api_key("openai", "sk-openai-test") is True
    assert gc.set_config_value("provider", "openai") is None
    client.app.state.config.session_provider = None
    client.app.state.config.provider = "openai"

    resp = client.patch("/api/config", json={"model": "gpt-4o-mini"})
    assert resp.status_code == 200

    # The running server now reports the new model (next prompt uses it).
    assert client.get("/api/config").json()["model"] == "gpt-4o-mini"


@requires_fastapi
def test_patch_model_for_other_provider_keeps_server_model(client):
    """A model set for a non-effective provider is persisted but does not
    change the running server's current model."""
    assert gc.set_config_value("provider", "openai") is None
    client.app.state.config.session_provider = None
    client.app.state.config.provider = "openai"
    client.app.state.config.model = "gpt-4o-mini"

    # Persist a model for a *different* provider (deepseek).
    resp = client.patch(
        "/api/config", json={"model": "deepseek-v4-flash", "provider": "deepseek"}
    )
    assert resp.status_code == 200

    # On disk for deepseek...
    assert (
        gc.load_config().get("providers", {}).get("deepseek", {}).get("model")
        == "deepseek-v4-flash"
    )
    # ...but the running server (openai) keeps its current model.
    assert client.get("/api/config").json()["model"] == "gpt-4o-mini"


@requires_fastapi
def test_patch_empty_model_clears_override(client):
    """An empty model removes the per-provider override from config.json."""
    assert gc.set_config_value("xai.model", "grok-4") is None
    assert gc.load_model_from_config("xai") == "grok-4"

    resp = client.patch("/api/config", json={"model": "", "provider": "xai"})
    assert resp.status_code == 200

    # The override is gone from disk (falls back to the built-in default).
    assert gc.load_config().get("providers", {}).get("xai", {}).get("model") is None


@requires_fastapi
def test_patch_model_unknown_provider_rejected(client):
    """An unknown provider name is rejected with 400 and nothing is written."""
    before = gc.load_config()
    resp = client.patch(
        "/api/config", json={"model": "whatever", "provider": "not-a-provider"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]
    assert gc.load_config() == before


@requires_fastapi
def test_patch_invalid_json_rejected(client):
    """A non-JSON body is rejected with 400."""
    resp = client.patch(
        "/api/config",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def test_settings_js_sends_provider_with_model():
    """settings.js persists the model scoped to the selected provider so it
    lands under the correct providers.<name>.model key."""
    js = (FRONTEND / "js" / "settings.js").read_text(encoding="utf-8")
    # The model edit is sent together with the provider it describes.
    assert "Api.patchConfig({" in js
    assert "model: this.model" in js
    assert "provider: this.selectedProvider" in js


def test_settings_js_prefers_selected_provider_model():
    """The Model field is pre-filled from the SELECTED provider's own model
    (configured or built-in default), not the running server's model."""
    js = (FRONTEND / "js" / "settings.js").read_text(encoding="utf-8")
    assert "this.model = this.defaultModel || this.config.model || '';" in js
