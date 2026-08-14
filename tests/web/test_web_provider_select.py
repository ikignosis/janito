"""Contract tests for the chat-page provider combo (issue #34).

The web chat's topbar provider switcher (``janito/web/frontend/js/providerSwitcher.js``)
lists the providers that have an API key set (``GET /api/config/providers``
→ ``api_key_set``) and switches the picked one **for the browser/server
session only** via ``POST /api/config/session-provider`` — it applies to the
next prompt but is NOT written to ``~/.janito/config.json``.

Persisting a default is a separate, explicit action (the Settings drawer's
"Set Default" button) backed by ``POST /api/config/default-provider``.

These tests pin down:

1. the providers endpoint response shape the combo renders from (incl. the
   ``effective`` flag the combo selects on);
2. that ``api_key_set`` mirrors the auth store contents;
3. that the session-provider endpoint switches the effective provider
   in memory WITHOUT touching config.json;
4. that the default-provider endpoint still persists (Settings drawer);
5. that both endpoints reject a provider without a key (``400``) and an
   unknown provider name (``400``) — the combo relies on this guard so the
   list of selectable providers is exactly the list that can be used.
"""

import sys
import tempfile
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from _frontend import render_index_html

import janito.auth_config as ac
import janito.config_dir as config_dir_mod
import janito.config_store as cs
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

    ``WebServerConfig.provider/model`` are mutated by the default-provider
    endpoint (mirrored into the running server), so the class-level defaults
    are restored afterwards to keep other test modules unaffected.
    """
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_provider_tests_")
    config_dir_mod.set_config_dir(tmp)

    from janito.web.backend.config import WebServerConfig

    prev = (WebServerConfig.provider, WebServerConfig.model)
    WebServerConfig.provider = None
    WebServerConfig.model = None

    def restore():
        config_dir_mod.set_config_dir(str(prev_dir))
        WebServerConfig.provider, WebServerConfig.model = prev

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
# GET /api/config/providers — the data the combo renders from
# ---------------------------------------------------------------------------


@requires_fastapi
def test_providers_endpoint_shape(client):
    """Each provider entry carries the fields the combo reads."""
    resp = client.get("/api/config/providers")
    assert resp.status_code == 200

    data = resp.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)
    assert data["providers"]  # non-empty

    for entry in data["providers"]:
        assert isinstance(entry["name"], str)
        assert entry["name"]
        assert isinstance(entry["api_key_set"], bool)
        assert isinstance(entry["active"], bool)
        assert isinstance(entry["effective"], bool)
        assert "model" in entry
        assert "default_model" in entry
        assert "default_max_input_tokens" in entry
        assert "default_max_output_tokens" in entry
        assert "default_thinking" in entry

    names = {entry["name"] for entry in data["providers"]}
    assert "openai" in names

    # DeepSeek and Alibaba/Qwen advertise thinking by default; openai does not.
    by_name = {entry["name"]: entry for entry in data["providers"]}
    assert by_name["deepseek"]["default_thinking"] is True
    assert by_name["alibaba"]["default_thinking"] is True
    assert by_name["openai"]["default_thinking"] in (None, False)

    # Exactly one provider is the effective one the next prompt uses.
    effective = [e for e in data["providers"] if e["effective"]]
    assert len(effective) == 1

    # session_provider is exposed at the top level (None until the combo
    # switches it for this session).
    assert "session_provider" in data


@requires_fastapi
def test_providers_api_key_set_mirrors_auth_store(client):
    """api_key_set flips with the contents of auth.json."""
    resp = client.get("/api/config/providers")
    entries = {p["name"]: p for p in resp.json()["providers"]}
    assert entries["openai"]["api_key_set"] is False

    assert ac.set_api_key("openai", "sk-test-123") is True

    resp = client.get("/api/config/providers")
    entries = {p["name"]: p for p in resp.json()["providers"]}
    assert entries["openai"]["api_key_set"] is True


# ---------------------------------------------------------------------------
# POST /api/config/session-provider — what the topbar combo triggers (session-only)
# ---------------------------------------------------------------------------


@requires_fastapi
def test_session_provider_switch_does_not_persist(client):
    """The combo's switch is in-memory only — config.json stays untouched."""
    # Establish a persisted default so we can prove it is unchanged.
    assert ac.set_api_key("openai", "sk-openai-test") is True
    assert cs.set_config_value("provider", "openai") is None
    assert ac.set_api_key("alibaba", "sk-alibaba-test") is True

    before = gc.load_provider_from_config()
    assert before == "openai"

    resp = client.post("/api/config/session-provider", json={"provider": "alibaba"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "alibaba"
    assert body["persisted"] is False

    # The persisted default must be UNCHANGED (the whole point).
    assert gc.load_provider_from_config() == "openai"

    # ...but the session now reports alibaba as the effective provider.
    status = client.get("/api/config/status")
    assert status.json()["provider"] == "alibaba"
    # active_provider still reports the persisted default.
    assert status.json()["active_provider"] == "openai"

    # The providers list flags alibaba as effective, openai as active.
    entries = {
        p["name"]: p for p in client.get("/api/config/providers").json()["providers"]
    }
    assert entries["alibaba"]["effective"] is True
    assert entries["openai"]["effective"] is False
    assert entries["openai"]["active"] is True

    # Reset the in-memory override so later tests start clean.
    client.app.state.config.session_provider = None


@requires_fastapi
def test_session_provider_without_key_is_rejected(client):
    """A session switch to a keyless provider is rejected (400), no change."""
    assert cs.set_config_value("provider", "openai") is None

    resp = client.post("/api/config/session-provider", json={"provider": "xai"})
    assert resp.status_code == 400
    assert "No API key" in resp.json()["detail"]

    # Nothing applied in memory either.
    assert client.app.state.config.session_provider in (None, "openai")
    assert gc.load_provider_from_config() == "openai"


@requires_fastapi
def test_session_provider_invalid_name_rejected(client):
    resp = client.post(
        "/api/config/session-provider", json={"provider": "not-a-provider"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/config/default-provider — Settings drawer "Set Default" (persists)
# ---------------------------------------------------------------------------


@requires_fastapi
def test_default_provider_switch_with_key_persists(client):
    """Setting a provider that has a key makes it the default everywhere."""
    assert ac.set_api_key("minimax", "sk-minimax-test") is True

    resp = client.post("/api/config/default-provider", json={"provider": "minimax"})
    assert resp.status_code == 200
    assert resp.json()["provider"] == "minimax"

    # Persisted for future CLI/web runs...
    assert gc.load_provider_from_config() == "minimax"

    # ...and mirrored into the running server.
    status = client.get("/api/config/status")
    assert status.json()["active_provider"] == "minimax"


@requires_fastapi
def test_default_provider_without_key_is_rejected(client):
    """A provider without a stored key cannot be promoted (400)."""
    # Make sure there is a valid current default first.
    assert ac.set_api_key("openai", "sk-openai-test") is True
    resp = client.post("/api/config/default-provider", json={"provider": "openai"})
    assert resp.status_code == 200

    # 'zai' has no key in the isolated auth store.
    resp = client.post("/api/config/default-provider", json={"provider": "zai"})
    assert resp.status_code == 400
    assert "No API key" in resp.json()["detail"]

    # The default must be unchanged.
    assert gc.load_provider_from_config() == "openai"


@requires_fastapi
def test_default_provider_invalid_name_rejected(client):
    """Unknown provider names are still rejected with 400."""
    resp = client.post(
        "/api/config/default-provider", json={"provider": "not-a-provider"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def test_index_html_wires_provider_switcher():
    """index.html loads the switcher script and renders the combo."""
    html = render_index_html()
    assert "/js/providerSwitcher.js" in html
    assert 'class="provider-combo"' in html
    assert "providerSwitcherComponent()" in html


def test_provider_switcher_js_contract():
    """The switcher component uses the providers API + session-only switch."""
    js = (FRONTEND / "js" / "providerSwitcher.js").read_text(encoding="utf-8")
    assert "Api.getProviders" in js
    # The combo switches the provider for the session only (never persists).
    assert "Api.setSessionProvider" in js
    assert "setDefaultProvider" not in js
    assert "api_key_set" in js
    assert "effective" in js
    assert "applyProvider" in js
    assert "janito-provider-changed" in js


def test_api_js_exposes_session_provider():
    """api.js offers a session-only switch distinct from the persisting one."""
    js = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    assert "setSessionProvider" in js
    assert "/api/config/session-provider" in js
    # The persisting endpoint still exists (Settings drawer "Set Default").
    assert "setDefaultProvider" in js
    assert "/api/config/default-provider" in js


def test_status_bar_reacts_to_provider_change():
    """The status bar reloads when the combo switches the provider."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    assert "janito-provider-changed" in js


def test_status_bar_resolves_provider_default_model():
    """The status bar loads the providers list and falls back to the selected
    provider's default model when no model is explicitly configured."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    # The providers list is loaded so the default can be resolved.
    assert "Api.getProviders" in js
    assert "this.providers = (await Api.getProviders()).providers || [];" in js
    # The selected provider is looked up by the effective provider name.
    assert "get providerDetail()" in js
    assert "p.name === this.provider" in js
    # Resolution mirrors the provider switcher/settings: configured override
    # first, then the provider's built-in default.
    assert "get defaultModel()" in js
    assert "p.model || p.default_model" in js
    # The model getter falls back to the provider default when the runtime
    # config/status carries no model.
    assert "this.defaultModel" in js
    # ...and a flag tells the template when the shown name is that fallback.
    assert "get modelIsDefault()" in js
    assert "!!this.defaultModel" in js


def test_index_html_status_bar_shows_default_model_instead_of_not_set():
    """The status bar renders the selected provider's default model (marked
    '(default)') instead of '(not set)' when no model is configured; '(not
    set)' remains only as a last resort when even the provider has none."""
    html = render_index_html()
    # The fallback marker is bound to the modelIsDefault flag.
    assert "model && modelIsDefault" in html
    assert "(default)" in html
    # '(not set)' is still there for the no-default-at-all case.
    assert "(not set)" in html
