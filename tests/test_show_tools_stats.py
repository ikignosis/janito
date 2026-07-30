"""
Tests for the ``/show_tools_stats`` shell command.

The command reads the per-tool invocation counters from the SQLite
``tools_use.db`` database (see :mod:`janito.tooling.tools_usage`) and renders
them as a ``rich`` table. These tests point the config dir at a temporary
directory, record some usage, and verify the command's matching, table
construction and rendered output.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.tooling.tools_usage as tools_usage
from janito.shell.cmds.show_tools_stats import ShowToolsStatsCmdHandler


def _point_at(monkeypatch, tmp_path):
    """Point the global config dir at a temp directory and return it."""
    config_dir = tmp_path / "custom_janito"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_dir)
    return config_dir


class _DummyShell:
    """Minimal stand-in for InteractiveShell (not used by this command)."""


def _render(handler, uses):
    """Render the stats table to a plain string via a rich Console."""
    from rich.console import Console

    console = Console(width=100, file=None)
    with console.capture() as capture:
        console.print(handler._build_table(uses))
    return capture.get()


if pytest is not None:

    def test_command_matches_only_its_name():
        handler = ShowToolsStatsCmdHandler()
        shell = _DummyShell()
        assert handler.name == "/show_tools_stats"
        assert handler.handle(shell, "/show_tools_stats") is True
        assert handler.handle(shell, "/SHOW_TOOLS_STATS") is True
        assert handler.handle(shell, "  /show_tools_stats  ") is True
        assert handler.handle(shell, "/tools") is False
        assert handler.handle(shell, "hello") is False

    def test_command_is_registered():
        from janito.shell.cmds import get_registered_commands

        names = [cmd.name for cmd in get_registered_commands()]
        assert "/show_tools_stats" in names

    def test_table_built_from_recorded_usage(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)

        for _ in range(3):
            tools_usage.record_tool_use("RunBashCode")
        tools_usage.record_tool_use("ReadFile")
        for _ in range(2):
            tools_usage.record_tool_use("ListFiles")

        handler = ShowToolsStatsCmdHandler()
        uses = tools_usage.get_all_tool_uses()
        table = handler._build_table(uses)

        # One row per tool plus the total footer row.
        assert table.row_count == len(uses) + 1
        assert table.columns[1].header == "Tool"

        output = _render(handler, uses)
        # Most-used tool appears first; totals are summed correctly.
        assert "RunBashCode" in output
        assert "ListFiles" in output
        assert "ReadFile" in output
        assert "Total" in output
        assert output.index("RunBashCode") < output.index("ReadFile")

    def test_empty_stats_prints_message(monkeypatch, tmp_path):
        import io
        from contextlib import redirect_stdout

        _point_at(monkeypatch, tmp_path)

        handler = ShowToolsStatsCmdHandler()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            handler._print_stats()
        assert "No tool usage recorded yet" in buffer.getvalue()

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(_MP(), Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
