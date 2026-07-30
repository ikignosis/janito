"""
Tests for the changes tracking (:mod:`janito.tooling.changes`) and the
``/changes`` shell command.

``janito.tooling.changes`` records, to ``./.janito/changes.jsonl``, every
*successful* tool call whose *first* argument is named ``filepath`` (only the
tool name and parameters — never the result). The file is removed by
``clear_changes()`` before a new prompt is processed. The ``/changes`` command
reads the file back and renders each execution in a friendly format:
``CreateFile`` content and ``ReplaceTextInFile`` diffs are syntax-highlighted,
and other tools are shown as pretty-printed JSON.

The state lives on disk under the current working directory, so every test
changes into a temporary directory.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.changes as changes
from janito.shell.cmds.changes import ChangesCmdHandler


class _DummyShell:
    """Minimal stand-in for InteractiveShell (not used by this command)."""


def _capture_render():
    """Render the changes report to a string via a capturing rich Console."""
    from rich.console import Console

    console = Console(width=100, force_terminal=False, color_system=None)
    with console.capture() as capture:
        changes.render_changes(console)
    return capture.get()


if pytest is not None:

    @pytest.fixture(autouse=True)
    def _isolate_cwd(tmp_path, monkeypatch):
        """Run each test in its own temp CWD so the changes file is isolated."""
        monkeypatch.chdir(tmp_path)
        yield tmp_path

    def test_changes_file_path_is_under_dot_janito(tmp_path):
        path = changes.get_changes_file_path()
        assert path == tmp_path / ".janito" / "changes.jsonl"

    def test_records_change_when_first_arg_is_filepath():
        changes.record_change("CreateFile", {"filepath": "a.py", "content": "x"})
        assert changes.load_changes() == [
            {"tool": "CreateFile", "params": {"filepath": "a.py", "content": "x"}}
        ]

    def test_first_arg_not_filepath_is_ignored():
        changes.record_change("SearchText", {"query": "x", "filepath": "a.py"})
        assert changes.load_changes() == []

    def test_read_only_tool_with_filepath_is_ignored():
        # Read-only tools (permissions "r") also take a "filepath" first arg
        # but make no changes, so they must not be tracked. These use real
        # built-in tool names resolved against the live tools registry.
        changes.record_change("ReadFile", {"filepath": "a.py"})
        changes.record_change("ListFiles", {"filepath": "a.py"})
        changes.record_change("SearchText", {"filepath": "a.py"})
        assert changes.load_changes() == []

    def test_write_permission_tools_are_recorded():
        # Only tools whose permissions include "w" are tracked (real built-in
        # tool names resolved against the live tools registry).
        changes.record_change("CreateFile", {"filepath": "a.py", "content": "x"})
        changes.record_change(
            "ReplaceTextInFile",
            {"filepath": "b.py", "old_str": "x", "new_str": "y"},
        )
        changes.record_change("MoveFile", {"filepath": "c.py", "destination": "d.py"})
        assert [r["tool"] for r in changes.load_changes()] == [
            "CreateFile",
            "ReplaceTextInFile",
            "MoveFile",
        ]

    def test_has_write_permission_matches_registry():
        # Sanity-check the permission helper against real built-in tools.
        assert changes._has_write_permission("CreateFile") is True
        assert changes._has_write_permission("ReplaceTextInFile") is True
        assert changes._has_write_permission("MoveFile") is True
        assert changes._has_write_permission("ReadFile") is False
        assert changes._has_write_permission("ListFiles") is False

    def test_unknown_tool_fails_open_and_is_recorded():
        # Tools the registry does not know about (e.g. MCP tools, which are
        # not tagged with permission flags) fail open so genuine changes are
        # never silently dropped.
        assert changes._has_write_permission("SomeUnknownMcpTool") is True
        changes.record_change(
            "SomeUnknownMcpTool", {"filepath": "a.py", "content": "x"}
        )
        assert [r["tool"] for r in changes.load_changes()] == ["SomeUnknownMcpTool"]

    def test_empty_tool_name_is_ignored():
        changes.record_change("", {"filepath": "a.py"})
        assert changes.load_changes() == []

    def test_non_dict_args_is_ignored():
        changes.record_change("CreateFile", ["a.py"])
        changes.record_change("CreateFile", None)
        assert changes.load_changes() == []

    def test_empty_args_is_ignored():
        changes.record_change("CreateFile", {})
        assert changes.load_changes() == []

    def test_non_string_or_empty_path_is_ignored():
        changes.record_change("CreateFile", {"filepath": 123})
        changes.record_change("CreateFile", {"filepath": None})
        changes.record_change("CreateFile", {"filepath": ""})
        assert changes.load_changes() == []

    def test_multiple_records_keep_insertion_order():
        changes.record_change("CreateFile", {"filepath": "first.py", "content": "a"})
        changes.record_change(
            "ReplaceTextInFile",
            {"filepath": "second.py", "old_str": "x", "new_str": "y"},
        )
        records = changes.load_changes()
        assert [r["params"]["filepath"] for r in records] == ["first.py", "second.py"]

    def test_only_params_are_recorded_not_results():
        # The recorder receives the call parameters; the result is never passed
        # in, so there is nothing but params in the stored record.
        changes.record_change("CreateFile", {"filepath": "a.py", "content": "x"})
        record = changes.load_changes()[0]
        assert set(record.keys()) == {"tool", "params"}

    def test_clear_changes_removes_file():
        changes.record_change("CreateFile", {"filepath": "a.py", "content": "x"})
        assert changes.get_changes_file_path().exists()
        assert changes.clear_changes() is True
        assert not changes.get_changes_file_path().exists()
        assert changes.load_changes() == []

    def test_clear_changes_when_no_file_returns_false():
        assert changes.clear_changes() is False

    def test_load_changes_skips_malformed_lines(tmp_path):
        path = changes.get_changes_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"tool": "CreateFile", "params": {"filepath": "a.py"}}\n'
            "not json\n"
            "\n",
            encoding="utf-8",
        )
        records = changes.load_changes()
        assert len(records) == 1
        assert records[0]["tool"] == "CreateFile"

    def test_render_empty_prints_friendly_message():
        output = _capture_render()
        assert "No changes recorded" in output

    def test_render_create_file_shows_content():
        changes.record_change(
            "CreateFile", {"filepath": "a.py", "content": "def hello():\n    pass"}
        )
        output = _capture_render()
        assert "CreateFile" in output
        assert "hello" in output

    def test_render_replace_text_shows_diff():
        changes.record_change(
            "ReplaceTextInFile",
            {"filepath": "a.py", "old_str": "foo = 1", "new_str": "foo = 2"},
        )
        output = _capture_render()
        assert "ReplaceTextInFile" in output
        # Unified diff markers are present.
        assert "-foo = 1" in output
        assert "+foo = 2" in output

    def test_render_other_tool_shows_params_json():
        changes.record_change("MoveFile", {"filepath": "a.py", "destination": "b.py"})
        output = _capture_render()
        assert "MoveFile" in output
        assert "destination" in output
        assert "b.py" in output

    def test_command_matches_only_its_name():
        handler = ChangesCmdHandler()
        shell = _DummyShell()
        assert handler.name == "/changes"
        assert handler.handle(shell, "/changes") is True
        assert handler.handle(shell, "/CHANGES") is True
        assert handler.handle(shell, "  /changes  ") is True
        assert handler.handle(shell, "/tools") is False
        assert handler.handle(shell, "hello") is False

    def test_command_is_registered():
        from janito.shell.cmds import get_registered_commands

        names = [cmd.name for cmd in get_registered_commands()]
        assert "/changes" in names

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def chdir(self, path):
                import os

                os.chdir(path)

            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    import os

                    prev = os.getcwd()
                    os.chdir(d)
                    try:
                        try:
                            fn(Path(d))
                        except TypeError:
                            fn()
                    finally:
                        os.chdir(prev)
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
