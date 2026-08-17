"""
Tests for the ToolsRegistry class (janito.tooling.tools_registry).

The registry's state intentionally lives at module level (AVAILABLE_TOOLS /
_tools_initialized / _loaded_toolsets / _skills_enabled) because the existing
tests monkeypatch those names directly.  These tests exercise the class API
over that state, isolating each test by monkeypatching the module state and
the discovery hooks (so no real filesystem scan ever runs).
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry
from janito.tooling.tools_registry import ToolsRegistry


def _fake_tool(name, permissions=""):
    def fake(**kwargs):
        return {"success": True}

    fake.__name__ = name
    fake._tool_permissions = permissions
    return fake


def _fresh_registry(monkeypatch, tools=None, skills_enabled=True):
    """Return a ToolsRegistry over isolated module state (no real discovery)."""
    tools = tools if tools is not None else {}
    monkeypatch.setattr(tools_registry, "AVAILABLE_TOOLS", dict(tools))
    monkeypatch.setattr(tools_registry, "_tools_initialized", False)
    monkeypatch.setattr(
        tools_registry,
        "_loaded_toolsets",
        set(tools_registry.AUTOLOAD_TOOLSETS),
    )
    monkeypatch.setattr(tools_registry, "_skills_enabled", skills_enabled)
    monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
    monkeypatch.setattr(tools_registry, "discover_toolsets", lambda names: {})
    monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: {})
    monkeypatch.setattr(tools_registry, "get_skills_advertisement", lambda: "")
    return ToolsRegistry()


if pytest is not None:

    def test_ensure_initialized_runs_discovery_once(monkeypatch):
        calls = {"n": 0}

        def fake_discover(names):
            calls["n"] += 1
            return {"FakeTool": _fake_tool("FakeTool", "r")}

        monkeypatch.setattr(tools_registry, "discover_toolsets", fake_discover)
        monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: {})
        monkeypatch.setattr(tools_registry, "AVAILABLE_TOOLS", {})
        monkeypatch.setattr(tools_registry, "_tools_initialized", False)
        monkeypatch.setattr(tools_registry, "_skills_enabled", False)

        registry = ToolsRegistry()
        registry.ensure_initialized()
        registry.ensure_initialized()
        assert calls["n"] == 1
        assert "FakeTool" in tools_registry.AVAILABLE_TOOLS

    def test_all_tools_and_schemas_and_permissions(monkeypatch):
        registry = _fresh_registry(
            monkeypatch,
            {
                "ReadFile": _fake_tool("ReadFile", "r"),
                "CreateFile": _fake_tool("CreateFile", "w"),
            },
        )
        assert set(registry.all_tools()) == {"ReadFile", "CreateFile"}
        schemas = registry.all_schemas()
        assert {s["function"]["name"] for s in schemas} == {"ReadFile", "CreateFile"}
        assert registry.all_permissions() == {"ReadFile": "r", "CreateFile": "w"}

    def test_get_schema_permissions(monkeypatch):
        registry = _fresh_registry(
            monkeypatch, {"ReadFile": _fake_tool("ReadFile", "r")}
        )
        assert registry.get("ReadFile") is not None
        assert registry.schema("ReadFile")["function"]["name"] == "ReadFile"
        assert registry.permissions("ReadFile") == "r"
        with pytest.raises(KeyError):
            registry.get("Missing")
        with pytest.raises(KeyError):
            registry.schema("Missing")
        with pytest.raises(KeyError):
            registry.permissions("Missing")

    def test_add_toolset_loads_new_tools_once(monkeypatch):
        calls = {"n": 0}
        registry = _fresh_registry(monkeypatch, {})

        def fake_discover(names):
            calls["n"] += 1
            return (
                {"GmailTool": _fake_tool("GmailTool", "r")} if "gmail" in names else {}
            )

        monkeypatch.setattr(tools_registry, "discover_toolsets", fake_discover)

        assert registry.add_toolset("gmail") is True
        assert "GmailTool" in registry.all_tools()
        # Discovery ran once for the autoload toolsets and once for "gmail".
        assert calls["n"] == 2
        # Already loaded: second call returns False without re-discovering.
        assert registry.add_toolset("gmail") is False
        assert calls["n"] == 2

    def test_add_toolset_no_tools_returns_false(monkeypatch):
        registry = _fresh_registry(monkeypatch, {})
        monkeypatch.setattr(tools_registry, "discover_toolsets", lambda names: {})
        # discover_toolsets returns {} -> nothing added -> False.
        assert registry.add_toolset("empty_toolset") is False
        assert "empty_toolset" in tools_registry._loaded_toolsets

    def test_enable_disable_skills(monkeypatch):
        skill_tools = {
            "load_skill": _fake_tool("load_skill"),
            "read_skill_resource": _fake_tool("read_skill_resource"),
        }
        registry = _fresh_registry(monkeypatch, {}, skills_enabled=True)
        monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: skill_tools)
        monkeypatch.setattr(
            tools_registry, "get_skills_advertisement", lambda: "## Available Skills"
        )

        registry.ensure_initialized()
        assert "load_skill" in registry.all_tools()
        assert "## Available Skills" in registry.skills_section()

        registry.disable_skills()
        assert "load_skill" not in registry.all_tools()
        assert registry.skills_section() == ""

        registry.enable_skills()
        assert "load_skill" in registry.all_tools()

    def test_disable_tools_loading_skips_autoload_keeps_skills(monkeypatch):
        """--no-tools: autoload toolsets are skipped, skill tools stay loaded."""
        skill_tools = {
            "load_skill": _fake_tool("load_skill"),
            "read_skill_resource": _fake_tool("read_skill_resource"),
        }
        calls = {"n": 0}
        registry = _fresh_registry(monkeypatch, {}, skills_enabled=True)
        monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: skill_tools)

        def fake_discover(names):
            calls["n"] += 1
            return {"ReadFile": _fake_tool("ReadFile", "r")}

        monkeypatch.setattr(tools_registry, "discover_toolsets", fake_discover)
        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)

        registry.ensure_initialized()

        # Autoload discovery never ran; only the skill tools are available.
        assert calls["n"] == 0
        assert set(registry.all_tools()) == {"load_skill", "read_skill_resource"}

    def test_disable_tools_loading_makes_add_toolset_noop(monkeypatch):
        calls = {"n": 0}
        registry = _fresh_registry(monkeypatch, {}, skills_enabled=False)

        def fake_discover(names):
            calls["n"] += 1
            return {"GmailTool": _fake_tool("GmailTool", "r")}

        monkeypatch.setattr(tools_registry, "discover_toolsets", fake_discover)
        monkeypatch.setattr(tools_registry, "get_skills_tools", lambda: {})
        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)

        # add_toolset is a no-op when loading is disabled...
        assert registry.add_toolset("gmail") is False
        # ...and it must not have triggered discovery for the autoload
        # toolsets either (the early return skips ensure_initialized).
        assert calls["n"] == 0
        assert "GmailTool" not in registry.all_tools()

    def test_register_plugin_tools_not_gated_by_no_tools(monkeypatch):
        """Plugin tools are registered even with --no-tools."""
        registry = _fresh_registry(monkeypatch, {}, skills_enabled=False)
        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)

        plugin_tool = _fake_tool("PluginTool", "r")
        registry.register_plugin_tools({"PluginTool": plugin_tool})

        assert "PluginTool" in registry.all_tools()

    def test_tools_loading_flag_module_delegators(monkeypatch):
        """Module-level disable_tools_loading / tools_loading_enabled."""
        _fresh_registry(monkeypatch, {})
        assert tools_registry.tools_loading_enabled() is True
        tools_registry.disable_tools_loading()
        assert tools_registry.tools_loading_enabled() is False

    def test_skills_section_empty_when_disabled(monkeypatch):
        registry = _fresh_registry(monkeypatch, {}, skills_enabled=False)
        assert registry.skills_section() == ""

    def test_module_functions_delegate_to_registry(monkeypatch):
        """The module-level functions behave identically to the class API."""
        registry = _fresh_registry(
            monkeypatch, {"ReadFile": _fake_tool("ReadFile", "r")}
        )
        assert tools_registry.get_all_tools() == registry.all_tools()
        assert tools_registry.get_all_tool_schemas() == registry.all_schemas()
        assert tools_registry.get_all_tool_permissions() == registry.all_permissions()
        assert tools_registry.get_tool_by_name("ReadFile") == registry.get("ReadFile")
        assert tools_registry.get_tool_schema_by_name("ReadFile") == registry.schema(
            "ReadFile"
        )
        assert tools_registry.get_tool_permissions("ReadFile") == registry.permissions(
            "ReadFile"
        )

    def test_module_singleton_is_a_registry():
        assert isinstance(tools_registry._registry, ToolsRegistry)

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                try:
                    fn(mp)
                finally:
                    mp.restore()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
