"""Backend + frontend wiring tests for the Settings drawer's Advanced section.

The Settings drawer (``janito/web/frontend/index.html`` + ``settings.js``)
gains an "Advanced" section (collapsed by default) with three per-provider
fields:

* ``endpoint`` -- base-URL override (``providers.<name>.endpoint``);
* ``api_type`` -- a combobox with one option per supported API type
  (``providers.<name>.api-type``, "Responses"/"Completions");
* ``responses_in_server`` -- a toggleable switch, only rendered while the
  API type is "Responses" (``providers.<name>.responses-in-server``).

All three are persisted per provider via ``PATCH /api/config`` (like the
model) and exposed per provider via ``GET /api/config/providers``.  The
``responses_in_server`` override is also honoured at runtime by
``get_responses_in_server_from_provider`` (the CLI's Responses-API path),
so the toggle actually changes how the conversation is chained.

These tests pin down:

1. ``PATCH /api/config`` persists ``endpoint`` / ``api_type`` /
   ``responses_in_server`` under the right per-provider config keys and
   rejects invalid values / unknown providers with ``400``;
2. an empty ``endpoint`` / ``api_type`` clears the per-provider override;
3. the providers endpoint exposes the Advanced fields
   (``api_type``, ``supported_api_types``, ``responses_in_server``,
   ``default_responses_in_server``, ``responses_in_server_override``);
4. the frontend wiring: the Advanced section is a collapsed ``<details>``,
   the endpoint is a text input, the API type is a combobox, and the
   ResponsesInServer switch is gated on the Responses API type; Save
   persists only the changed Advanced fields and re-baselines the drawer.
"""

import sys
import tempfile
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

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
    """Isolate the config dir in a temp dir so tests never touch the real one."""
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_settings_advanced_tests_")
    config_dir_mod.set_config_dir(tmp)

    def restore():
        config_dir_mod.set_config_dir(str(prev_dir))

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


def _providers_by_name(client):
    data = client.get("/api/config/providers").json()
    return {p["name"]: p for p in data["providers"]}


# ---------------------------------------------------------------------------
# PATCH /api/config — Advanced section persistence
# ---------------------------------------------------------------------------


@requires_fastapi
def test_patch_endpoint_persists_per_provider(client):
    """{endpoint, provider} writes providers.<provider>.endpoint to config.json."""
    gc.unset_config_value("minimax.endpoint")

    resp = client.patch(
        "/api/config",
        json={"endpoint": "https://minimax.example/v1", "provider": "minimax"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["endpoint"] == "https://minimax.example/v1"

    assert (
        gc.load_config().get("providers", {}).get("minimax", {}).get("endpoint")
        == "https://minimax.example/v1"
    )
    # ...and the providers endpoint reflects the override (base_url wins).
    entry = _providers_by_name(client)["minimax"]
    assert entry["endpoint"] == "https://minimax.example/v1"
    assert entry["base_url"] == "https://minimax.example/v1"


@requires_fastapi
def test_patch_empty_endpoint_clears_override(client):
    """An empty endpoint removes the per-provider override (built-in returns)."""
    gc.set_config_value("minimax.endpoint", "https://minimax.example/v1")
    assert gc.load_endpoint_from_config("minimax") == "https://minimax.example/v1"

    resp = client.patch("/api/config", json={"endpoint": "", "provider": "minimax"})
    assert resp.status_code == 200
    assert resp.json()["updated"]["endpoint"] == ""

    assert (
        gc.load_config().get("providers", {}).get("minimax", {}).get("endpoint") is None
    )
    # Falls back to the built-in endpoint.
    assert (
        _providers_by_name(client)["minimax"]["base_url"] == "https://api.minimax.io/v1"
    )


@requires_fastapi
def test_patch_api_type_persists_and_normalizes(client):
    """api_type is canonicalized (Responses/Completions) and stored per provider."""
    gc.unset_config_value("openai.api-type")

    resp = client.patch(
        "/api/config", json={"api_type": "completions", "provider": "openai"}
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["api_type"] == "Completions"

    assert gc.load_api_type("openai") == "Completions"
    entry = _providers_by_name(client)["openai"]
    assert entry["api_type"] == "Completions"
    # The built-in default is still exposed separately.
    assert entry["default_api_type"] == "Responses"


@requires_fastapi
def test_patch_api_type_rejects_unknown_value(client):
    """A bogus API type is rejected with 400 and nothing is written."""
    gc.unset_config_value("openai.api-type")
    before = gc.load_config()

    resp = client.patch("/api/config", json={"api_type": "Bogus", "provider": "openai"})
    assert resp.status_code == 400
    assert "Unsupported API type" in resp.json()["detail"]
    assert gc.load_config() == before


@requires_fastapi
def test_patch_api_type_anthropic_aborts_without_package(client):
    """The native Anthropic SDK API type is rejected with 400 (nothing is
    written) when the optional `anthropic` package is not installed, with a
    message naming the package."""
    gc.unset_config_value("anthropic.api-type")
    before = gc.load_config()

    resp = client.patch(
        "/api/config", json={"api_type": "Anthropic", "provider": "anthropic"}
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Anthropic" in detail
    assert "anthropic" in detail
    assert "pip install anthropic" in detail
    assert gc.load_config() == before


@requires_fastapi
def test_patch_api_type_empty_clears_override(client):
    """An empty api_type removes the per-provider override."""
    gc.set_config_value("openai.api-type", "Completions")
    assert gc.load_api_type("openai") == "Completions"

    resp = client.patch("/api/config", json={"api_type": "", "provider": "openai"})
    assert resp.status_code == 200
    assert resp.json()["updated"]["api_type"] == ""

    assert gc.load_api_type("openai") is None
    assert _providers_by_name(client)["openai"]["api_type"] is None


@requires_fastapi
def test_patch_responses_in_server_persists(client):
    """responses_in_server is stored per provider and exposed effectively."""
    gc.unset_config_value("openai.responses-in-server")

    resp = client.patch(
        "/api/config",
        json={"responses_in_server": False, "provider": "openai"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["responses_in_server"] is False

    assert gc.load_responses_in_server_from_config("openai") is False
    entry = _providers_by_name(client)["openai"]
    assert entry["responses_in_server"] is False  # override wins
    assert entry["default_responses_in_server"] is True  # built-in unchanged
    assert entry["responses_in_server_override"] is False


@requires_fastapi
def test_patch_responses_in_server_accepts_string_bool(client):
    """String forms true/false/1/0 are coerced to booleans."""
    resp = client.patch(
        "/api/config",
        json={"responses_in_server": "true", "provider": "deepseek"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["responses_in_server"] is True
    assert gc.load_responses_in_server_from_config("deepseek") is True

    resp = client.patch(
        "/api/config",
        json={"responses_in_server": "0", "provider": "deepseek"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"]["responses_in_server"] is False


@requires_fastapi
def test_patch_responses_in_server_rejects_invalid(client):
    """A non-boolean responses_in_server is rejected with 400."""
    gc.unset_config_value("openai.responses-in-server")
    before = gc.load_config()

    resp = client.patch(
        "/api/config",
        json={"responses_in_server": "maybe", "provider": "openai"},
    )
    assert resp.status_code == 400
    assert "must be a boolean" in resp.json()["detail"]
    assert gc.load_config() == before


@requires_fastapi
def test_patch_advanced_unknown_provider_rejected(client):
    """An unknown provider name is rejected with 400 and nothing is written."""
    before = gc.load_config()
    resp = client.patch(
        "/api/config",
        json={"endpoint": "https://x/v1", "provider": "not-a-provider"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]
    assert gc.load_config() == before


# ---------------------------------------------------------------------------
# GET /api/config/providers — the data the Advanced section renders from
# ---------------------------------------------------------------------------


@requires_fastapi
def test_providers_endpoint_exposes_advanced_fields(client):
    """Each provider entry carries the Advanced fields the drawer reads."""
    entries = _providers_by_name(client)

    openai = entries["openai"]
    # OpenAI supports both API types -> the drawer shows a combobox with both.
    assert openai["supported_api_types"] == ["Responses", "Completions"]
    assert openai["default_api_type"] == "Responses"
    assert "api_type" in openai  # configured override (None until set)
    # OpenAI's /responses endpoint is server-side by default.
    assert openai["responses_in_server"] is True
    assert openai["default_responses_in_server"] is True
    assert openai["responses_in_server_override"] is None
    assert "endpoint" in openai
    assert "base_url" in openai

    deepseek = entries["deepseek"]
    # DeepSeek supports both API types -> the drawer shows a combobox with
    # both options; Responses (the first supported type) is the built-in default.
    assert deepseek["supported_api_types"] == ["Responses", "Completions"]
    assert deepseek["default_api_type"] == "Responses"
    # DeepSeek's /responses endpoint is stateless by default.
    assert deepseek["responses_in_server"] is False
    assert deepseek["default_responses_in_server"] is False

    anthropic = entries["anthropic"]
    # Anthropic supports Completions (the built-in default) plus the native
    # Anthropic SDK API type; the per-API-type endpoint map is exposed so the
    # drawer could show per-type URLs.
    assert anthropic["supported_api_types"] == ["Completions", "Anthropic"]
    assert anthropic["default_api_type"] == "Completions"
    assert anthropic["endpoint_by_api_type"] == {
        "Completions": "https://api.anthropic.com/v1/",
        "Anthropic": "https://api.anthropic.com",
    }
    # base_url reflects the default API type's built-in endpoint.
    assert anthropic["base_url"] == "https://api.anthropic.com/v1/"


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def _html():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")


def _settings_js():
    return (FRONTEND / "js" / "settings.js").read_text(encoding="utf-8")


def test_index_html_advanced_section_collapsed_by_default():
    """The Advanced section is a <details> element WITHOUT the open attribute,
    so it starts collapsed; the summary is labelled 'Advanced'."""
    html = _html()
    assert '<details class="advanced-section">' in html
    assert "<summary>Advanced</summary>" in html
    # Collapsed by default: no `open` attribute on the details element.
    assert 'class="advanced-section" open' not in html
    assert 'advanced-section" open' not in html


def test_index_html_endpoint_field_wired():
    """The Endpoint is a text input bound to the component's endpoint state."""
    html = _html()
    assert 'x-model="endpoint"' in html
    assert 'id="endpoint-input"' in html
    assert "Leave empty to use the built-in endpoint" in html


def test_index_html_api_type_combobox():
    """The API type is a <select> combobox with one <option> per supported
    type, bound to the apiType state (works for both single- and
    multi-type providers)."""
    html = _html()
    # A real combobox, not plain text or radios...
    assert 'id="api-type-select"' in html
    assert '<select id="api-type-select" x-model="apiType">' in html
    assert 'type="radio"' not in html
    # ...with one option per supported API type.
    assert 'x-for="t in supportedApiTypes"' in html
    assert ':value="t" x-text="t"' in html


def test_index_html_responses_in_server_gated_on_responses():
    """The ResponsesInServer switch is only rendered while the API type is
    Responses and binds to the responsesInServer state."""
    html = _html()
    assert 'x-if="apiTypeIsResponses"' in html
    assert "ResponsesInServer" in html
    assert 'x-model="responsesInServer"' in html
    assert 'id="responses-in-server-toggle"' in html


def test_settings_js_advanced_state_and_baselines():
    """The component tracks the Advanced fields and their pristine baselines
    (like originalModel), so Save stays disabled until they change."""
    js = _settings_js()
    assert "endpoint: ''" in js
    assert "apiType: ''" in js
    assert "responsesInServer: false" in js
    assert "originalEndpoint: ''" in js
    assert "originalApiType: ''" in js
    assert "originalResponsesInServer: false" in js


def test_settings_js_resolves_api_type_from_provider():
    """resolveApiType mirrors the CLI: configured override first, then the
    provider's built-in default (first supported type)."""
    js = _settings_js()
    assert "resolveApiType()" in js
    assert "p.api_type ||" in js
    assert "p.default_api_type" in js
    assert "p.supported_api_types && p.supported_api_types[0]" in js
    # The toggle gate follows the effective API type.
    assert "get apiTypeIsResponses()" in js
    assert "this.apiType === 'Responses'" in js
    # The supported-types list drives the combobox options in the template.
    assert "get supportedApiTypes()" in js
    assert "p.supported_api_types" in js


def test_settings_js_can_save_includes_advanced():
    """Save is enabled when an Advanced field differs from its baseline."""
    js = _settings_js()
    assert "this.endpoint !== this.originalEndpoint" in js
    assert "this.apiType !== this.originalApiType" in js
    assert "this.responsesInServer !== this.originalResponsesInServer" in js


def test_settings_js_save_persists_advanced_changes():
    """Save sends only the changed Advanced fields, scoped to the selected
    provider, and re-baselines them afterwards."""
    js = _settings_js()
    assert "const advancedPatch = {};" in js
    assert "advancedPatch.endpoint = this.endpoint;" in js
    assert "advancedPatch.api_type = this.apiType;" in js
    assert "advancedPatch.responses_in_server = this.responsesInServer;" in js
    assert "advancedPatch.provider = this.selectedProvider;" in js
    assert "await Api.patchConfig(advancedPatch);" in js
    # Re-baseline after a successful save (drawer pristine again).
    assert "this.originalEndpoint = this.endpoint;" in js
    assert "this.originalApiType = this.apiType;" in js
    assert "this.originalResponsesInServer = this.responsesInServer;" in js


def test_drawers_css_styles_advanced_section():
    """drawers.css styles the collapsible Advanced section and its controls."""
    css = (FRONTEND / "css" / "drawers.css").read_text(encoding="utf-8")
    assert ".advanced-section" in css
    assert ".advanced-section summary" in css
    assert ".form-group select" in css  # styles the API type combobox
    assert ".switch-track" in css
    assert ".switch-input:checked + .switch-track" in css
    assert ".field-hint" in css
