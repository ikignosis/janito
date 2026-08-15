"""Contract tests for the web ``/tools`` panel data endpoints.

The web chat's ``/tools`` command (janito/web/frontend/js/chatCommands.js)
fetches three endpoints and renders their payloads as a formatted tools
panel. These tests pin down the exact response shapes the frontend relies on,
so a backend refactor that renames or restructures a field is caught here
rather than as a broken UI.

Endpoints under test:
    GET /api/tools          -> {"tools": [{name, description, permissions}], "count"}
    GET /api/tools/skipped  -> {"skipped": {name: reason}}
    GET /api/mcp/tools      -> {"tools": [openai schema], "count"}
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from _frontend import render_index_html

import janito.tooling.tools_registry as tools_registry


def _fake_tool(name, permissions=""):
    def fake(**kwargs):
        return {"success": True}

    fake.__name__ = name
    fake._tool_permissions = permissions
    return fake


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


@pytest.fixture()
def client():
    """A TestClient wired to a fresh Janito web app."""
    from janito.web.backend.app import create_app
    from janito.web.backend.config import WebServerConfig

    config = WebServerConfig(web_host="127.0.0.1", web_port=0, no_web_open=True)
    app = create_app(config)
    with TestClient(app) as c:
        yield c


@requires_fastapi
def test_tools_endpoint_shape(client):
    """GET /api/tools returns a list of tools with the fields the panel uses."""
    resp = client.get("/api/tools")
    assert resp.status_code == 200

    data = resp.json()
    assert "tools" in data
    assert "count" in data
    assert "tools_enabled" in data
    assert isinstance(data["tools"], list)
    assert data["count"] == len(data["tools"])
    # Tools are enabled by default; the frontend renders a warning when False.
    assert data["tools_enabled"] is True

    # The frontend reads name / description / permissions off each entry.
    for entry in data["tools"]:
        assert "name" in entry
        assert "description" in entry
        assert "permissions" in entry
        assert isinstance(entry["name"], str)
        assert entry["name"]  # non-empty

    # At least the always-loaded built-in tools should be present.
    names = {entry["name"] for entry in data["tools"]}
    assert "ReadFile" in names


@requires_fastapi
def test_tools_endpoint_reports_no_tools_disabled(monkeypatch):
    """GET /api/tools reports tools_enabled=False and only skill tools under --no-tools."""
    from janito.web.backend.app import create_app
    from janito.web.backend.config import WebServerConfig

    skill_tools = {
        "load_skill": _fake_tool("load_skill"),
        "read_skill_resource": _fake_tool("read_skill_resource"),
    }
    monkeypatch.setattr(tools_registry, "AVAILABLE_TOOLS", {})
    monkeypatch.setattr(tools_registry, "_tools_initialized", False)
    monkeypatch.setattr(
        tools_registry,
        "_loaded_toolsets",
        set(tools_registry.AUTOLOAD_TOOLSETS),
    )
    monkeypatch.setattr(tools_registry, "_skills_enabled", True)
    monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)
    monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: skill_tools)

    config = WebServerConfig(web_host="127.0.0.1", web_port=0, no_web_open=True)
    app = create_app(config)
    with TestClient(app) as c:
        data = c.get("/api/tools").json()

    assert data["tools_enabled"] is False
    names = {entry["name"] for entry in data["tools"]}
    assert names == {"load_skill", "read_skill_resource"}


@requires_fastapi
def test_tools_permissions_are_valid_flags(client):
    """Each built-in tool's permissions string uses only r/w/x flags."""
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    for entry in resp.json()["tools"]:
        perms = entry["permissions"]
        assert isinstance(perms, str)
        assert set(perms) <= {"r", "w", "x"}, f"bad permissions {perms!r}"


@requires_fastapi
def test_skipped_tools_endpoint_shape(client):
    """GET /api/tools/skipped returns a name->reason mapping."""
    resp = client.get("/api/tools/skipped")
    assert resp.status_code == 200

    data = resp.json()
    assert "skipped" in data
    assert isinstance(data["skipped"], dict)
    for name, reason in data["skipped"].items():
        assert isinstance(name, str)
        assert isinstance(reason, str)


@requires_fastapi
def test_mcp_tools_endpoint_shape(client):
    """GET /api/mcp/tools returns a list of OpenAI-formatted tool schemas."""
    resp = client.get("/api/mcp/tools")
    assert resp.status_code == 200

    data = resp.json()
    assert "tools" in data
    assert "count" in data
    assert isinstance(data["tools"], list)
    assert data["count"] == len(data["tools"])

    # When services are connected, entries are OpenAI schemas with a
    # ``function.name`` that the frontend unwraps via ``s.function || s``.
    for schema in data["tools"]:
        fn = schema.get("function", schema)
        assert "name" in fn


@requires_fastapi
def test_frontend_loads_tools_command_script():
    """index.html references the chatCommands.js slash-command mixin."""
    html = render_index_html()
    assert "/js/chatCommands.js" in html
    # The panel template block must be present.
    assert "part.kind === 'tools'" in html


@requires_fastapi
def test_chat_commands_mixin_intercepts_tools():
    """The chatCommands.js mixin defines the /tools dispatch + panel builder."""
    js = (
        Path(__file__).parent.parent.parent
        / "janito"
        / "web"
        / "frontend"
        / "js"
        / "chatCommands.js"
    )
    src = js.read_text(encoding="utf-8")
    assert "_handleSlashCommand" in src
    assert "'/tools'" in src
    assert "_runToolsCommand" in src
    assert "getMcpTools" in src


@requires_fastapi
def test_chat_commands_mixin_reads_tools_enabled():
    """The listing builder surfaces the API's tools_enabled flag for the banner."""
    js = (
        Path(__file__).parent.parent.parent
        / "janito"
        / "web"
        / "frontend"
        / "js"
        / "chatCommands.js"
    )
    src = js.read_text(encoding="utf-8")
    assert "data.tools_enabled" in src
    assert "toolsEnabled" in src
