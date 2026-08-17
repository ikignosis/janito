"""
Tests for the ``--no-tools`` CLI flag.

``--no-tools`` disables loading of non-skill tools: the registry never runs
``discover_toolsets`` for the autoload toolsets, ``add_toolset`` becomes a
no-op, and MCP tools are not loaded.  The skill tools (``load_skill`` /
``read_skill_resource``) stay enabled regardless.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry


def _fake_tool(name, permissions=""):
    def fake(**kwargs):
        return {"success": True}

    fake.__name__ = name
    fake._tool_permissions = permissions
    return fake


if pytest is not None:

    def test_parser_exposes_no_tools_flag():
        from janito.cli.parser import create_parser

        args = create_parser().parse_args(["--no-tools", "prompt"])
        assert args.no_tools is True
        # Default stays disabled.
        args = create_parser().parse_args(["prompt"])
        assert args.no_tools is False

    def test_parser_exposes_no_plugins_flag():
        from janito.cli.parser import create_parser

        args = create_parser().parse_args(["--no-plugins", "prompt"])
        assert args.no_plugins is True
        # Default stays disabled.
        args = create_parser().parse_args(["prompt"])
        assert args.no_plugins is False

    def test_parser_help_documents_no_tools_and_no_plugins():
        from janito.cli.parser import create_parser

        help_text = create_parser().format_help()
        assert "--no-tools" in help_text
        assert "skill tools stay enabled" in help_text
        assert "--no-plugins" in help_text

    def test_setup_runtime_applies_no_tools(monkeypatch):
        from janito import __main__

        class _Args:
            no_tools = True
            config_dir = None
            local = False
            log = None
            provider = None
            read = write = exec = False

        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
        assert __main__._setup_runtime(_Args()) is None
        assert tools_registry.tools_loading_enabled() is False

    def test_setup_runtime_leaves_tools_enabled_without_flag(monkeypatch):
        from janito import __main__

        class _Args:
            no_tools = False
            config_dir = None
            local = False
            log = None
            provider = None
            read = write = exec = False

        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
        assert __main__._setup_runtime(_Args()) is None
        assert tools_registry.tools_loading_enabled() is True

    def test_web_config_from_args_applies_no_tools(monkeypatch):
        from janito.cli.parser import create_parser
        from janito.web.backend.config import WebServerConfig

        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
        args = create_parser().parse_args(["--web", "--no-tools"])
        WebServerConfig.from_args(args)
        assert tools_registry.tools_loading_enabled() is False
        assert args.no_tools is True

    def test_web_config_cli_args_include_no_tools(monkeypatch):
        from janito.cli.parser import create_parser
        from janito.web.backend.config import WebServerConfig

        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
        args = create_parser().parse_args(["--web", "--no-tools"])
        config = WebServerConfig.from_args(args)
        assert config.cli_args["no_tools"] is True

    def test_registry_only_skill_tools_with_no_tools(monkeypatch):
        """--no-tools: autoload toolsets skipped, skill tools still present."""
        skill_tools = {
            "load_skill": _fake_tool("load_skill"),
            "read_skill_resource": _fake_tool("read_skill_resource"),
        }
        calls = {"n": 0}
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

        def fake_discover(names):
            calls["n"] += 1
            return {"ReadFile": _fake_tool("ReadFile", "r")}

        monkeypatch.setattr(tools_registry, "discover_toolsets", fake_discover)

        schemas = tools_registry.get_all_tool_schemas()
        names = {s["function"]["name"] for s in schemas}

        assert calls["n"] == 0  # autoload discovery never ran
        assert names == {"load_skill", "read_skill_resource"}

    def test_mcp_not_loaded_when_no_tools(monkeypatch):
        """--no-tools also suppresses MCP tool loading in the shared helper."""
        from janito.openai_client import client_support

        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)
        manager, tools = client_support._load_mcp(use_mcp=True)
        assert manager is None
        assert tools == []

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        class _MP:
            def setattr(self, obj, name, value):
                self._undo = getattr(self, "_undo", [])
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(getattr(self, "_undo", [])):
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
