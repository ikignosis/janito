"""
Tests for the shell ``/tools`` command.

The command prints the loaded built-in, skipped and MCP tools as rich tables.
When the server is started with ``--no-tools`` (non-skill tools disabled), the
command must print a warning telling the user that tool loading is disabled and
only the skill tools remain available.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.tools_registry as tools_registry
from janito.shell.cmds.tools import ToolsCmdHandler


class _DummyShell:
    """Minimal stand-in for InteractiveShell (not used by this command)."""


if pytest is not None:

    def test_command_matches_only_its_name():
        handler = ToolsCmdHandler()
        shell = _DummyShell()
        assert handler.name == "/tools"
        assert handler.handle(shell, "/tools") is True
        assert handler.handle(shell, "/TOOLS") is True
        assert handler.handle(shell, "  /tools  ") is True
        assert handler.handle(shell, "/help") is False
        assert handler.handle(shell, "hello") is False

    def test_command_is_registered():
        from janito.shell.cmds import get_registered_commands

        names = [cmd.name for cmd in get_registered_commands()]
        assert "/tools" in names

    def test_warns_when_tools_disabled(monkeypatch, capfd):
        """--no-tools: /tools prints a warning about tool loading being disabled."""
        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", False)
        handler = ToolsCmdHandler()
        handler.handle(_DummyShell(), "/tools")
        out = capfd.readouterr().out
        assert "Warning" in out
        assert "--no-tools" in out
        assert "disabled" in out
        assert "load_skill" in out and "read_skill_resource" in out

    def test_no_warning_when_tools_enabled(monkeypatch, capfd):
        """Default mode: /tools prints no disabled-tools warning."""
        monkeypatch.setattr(tools_registry, "_tools_loading_enabled", True)
        handler = ToolsCmdHandler()
        handler.handle(_DummyShell(), "/tools")
        out = capfd.readouterr().out
        assert "--no-tools" not in out
        assert "Warning" not in out

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        class _MP:
            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn(_MP())
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
