"""Backend + frontend wiring tests for the status-bar thinking toggle.

The status bar's "thinking" badge is a runtime on/off button: clicking it
posts to ``POST /api/config/thinking``, which sets an in-memory override on
the running server (``WebServerConfig.thinking_override``).  The override is
NOT persisted to ``~/.janito/config.json`` (like the session-provider
override) and is lost on restart; it applies to the very next prompt and
forces the state in both directions (``false`` disables thinking even for
providers that reason by default, e.g. DeepSeek/Qwen).

``config.effective_thinking`` resolves: runtime override > ``--thinking``
CLI flag > provider built-in ``default_thinking``, and
``build_call_kwargs`` sends ``extra_body={'enable_thinking': True}`` exactly
when it is True.

These tests pin down:

1. ``POST /api/config/thinking`` sets the runtime override (explicit value
   and body-less toggle);
2. the override wins over the CLI ``--thinking`` flag and the provider
   default (both directions);
3. nothing is written to config.json;
4. ``build_call_kwargs`` honors the override;
5. the frontend wiring (index.html button + statusBar.js + api.js).
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
    tmp = tempfile.mkdtemp(prefix="janito_thinking_toggle_tests_")
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


def _reset(config):
    """Return the shared server config to a neutral baseline."""
    config.thinking_override = None
    config.thinking = False
    config.session_provider = None
    config.provider = None


# ---------------------------------------------------------------------------
# POST /api/config/thinking — the status-bar toggle
# ---------------------------------------------------------------------------


@requires_fastapi
def test_thinking_toggle_sets_runtime_state(client):
    """POST /api/config/thinking {thinking} sets the in-memory override and
    the config endpoint reports it as the effective state."""
    cfg = client.app.state.config
    _reset(cfg)

    resp = client.post("/api/config/thinking", json={"thinking": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["thinking"] is False
    assert body["effective"] is False
    assert body["persisted"] is False
    # The running server now reports thinking off for the next prompt.
    assert client.get("/api/config").json()["thinking"] is False

    resp = client.post("/api/config/thinking", json={"thinking": True})
    assert resp.json()["thinking"] is True
    assert client.get("/api/config").json()["thinking"] is True


@requires_fastapi
def test_thinking_toggle_without_body_flips_effective(client):
    """An empty body (or {"toggle": true}) flips the current effective value."""
    cfg = client.app.state.config
    _reset(cfg)

    assert cfg.effective_thinking is False  # openai-style default
    resp = client.post("/api/config/thinking")
    assert resp.json()["thinking"] is True

    resp = client.post("/api/config/thinking", json={"toggle": True})
    assert resp.json()["thinking"] is False


@requires_fastapi
def test_thinking_override_forces_off_for_default_thinking_provider(client):
    """DeepSeek reasons by default, but the toggle can force thinking off."""
    cfg = client.app.state.config
    _reset(cfg)
    cfg.provider = "deepseek"  # built-in default_thinking is True

    assert cfg.effective_thinking is True  # provider default
    resp = client.post("/api/config/thinking", json={"thinking": False})
    assert resp.json()["effective"] is False
    assert client.get("/api/config").json()["thinking"] is False


@requires_fastapi
def test_thinking_override_wins_over_cli_flag(client):
    """A runtime ``false`` beats the CLI --thinking flag; a runtime ``true``
    beats a provider without a default."""
    cfg = client.app.state.config
    _reset(cfg)
    cfg.thinking = True  # started with -t / --thinking
    assert cfg.effective_thinking is True

    resp = client.post("/api/config/thinking", json={"thinking": False})
    assert resp.json()["effective"] is False

    _reset(cfg)
    cfg.provider = "openai"  # no default thinking
    assert cfg.effective_thinking is False
    resp = client.post("/api/config/thinking", json={"thinking": True})
    assert resp.json()["effective"] is True


@requires_fastapi
def test_thinking_toggle_not_persisted_to_disk(client):
    """The toggle lives in memory only: config.json is left untouched."""
    cfg = client.app.state.config
    _reset(cfg)

    before = gc.load_config()
    client.post("/api/config/thinking", json={"thinking": True})
    client.post("/api/config/thinking", json={"thinking": False})
    assert gc.load_config() == before
    assert "thinking" not in gc.load_config()


@requires_fastapi
def test_build_call_kwargs_honors_runtime_override(client):
    """enable_thinking follows the runtime override in both directions."""
    from janito.web.backend.agent.call import build_call_kwargs

    cfg = client.app.state.config

    # Force off on a default-thinking provider -> no enable_thinking.
    _reset(cfg)
    cfg.provider = "deepseek"
    cfg.thinking_override = False
    kwargs = build_call_kwargs("deepseek-v4-flash", cfg, 1000, None, None)
    assert "extra_body" not in kwargs

    # Force on for a provider without a default -> enable_thinking sent.
    _reset(cfg)
    cfg.provider = "openai"
    cfg.thinking_override = True
    kwargs = build_call_kwargs("gpt-4", cfg, 1000, None, None)
    assert kwargs["extra_body"]["enable_thinking"] is True


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def test_index_html_thinking_badge_is_toggle_button():
    """The status-bar thinking element is a button that posts to the toggle."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'class="flag-badge flag-toggle"' in html
    assert '@click="toggleThinking()"' in html
    assert ':class="{ active: config.thinking }"' in html
    assert ":aria-pressed=\"config.thinking ? 'true' : 'false'\"" in html


def test_status_bar_js_toggles_thinking():
    """statusBar.js flips the effective value via Api.setThinking."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    assert "async toggleThinking()" in js
    assert "Api.setThinking(next)" in js
    # The badge mirrors what the next prompt actually uses.
    assert "this.config.thinking = data.effective;" in js


def test_api_js_exposes_set_thinking():
    """api.js wraps POST /api/config/thinking."""
    js = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    assert "setThinking(thinking)" in js
    assert "this.post('/api/config/thinking', { thinking })" in js


def test_css_styles_toggle_affordance():
    """The toggle badge gets an interactive cursor/hover/focus style."""
    css = (FRONTEND / "css" / "ui-controls.css").read_text(encoding="utf-8")
    assert ".flag-badge.flag-toggle" in css
    assert "cursor: pointer" in css
    assert ".flag-badge.flag-toggle:focus-visible" in css
