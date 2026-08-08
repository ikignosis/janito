"""
Tests for the in-process used-files tracking.

``janito.tooling.used_files`` records, in memory, every file path touched by a
tool call whose *first* argument is named ``filepath``. Depending on the tool's
declared permissions (``@tool(permissions="…")``), the path is appended to the
``READ`` list (permission contains ``'r'``) and/or the ``WRITE`` list
(permission contains ``'w'``). Filenames are unique per list.

Tracking is deliberately defensive (best-effort and never raises), so these
tests verify both the happy path and that invalid inputs are silently ignored.

Unlike ``tools_usage`` (SQLite-backed) the state here is a process-global dict,
so every test resets it via ``reset_used_files()``.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from rich.text import Text

import janito.tooling.tools_registry as tools_registry
import janito.tooling.used_files as used_files


def _register(monkeypatch, name, permissions):
    """Register a fake tool with the given permission string.

    Sets ``_tools_initialized`` so the registry never triggers the (slow,
    filesystem-scanning) real discovery, and injects a stub callable carrying
    the ``_tool_permissions`` attribute the tracker reads.
    """
    monkeypatch.setattr(tools_registry, "_tools_initialized", True)
    fake = lambda **kwargs: {"success": True}  # noqa: E731
    fake._tool_permissions = permissions
    monkeypatch.setitem(tools_registry.AVAILABLE_TOOLS, name, fake)


if pytest is not None:

    @pytest.fixture(autouse=True)
    def _clean_state():
        """Ensure each test starts from (and leaves behind) empty state."""
        used_files.reset_used_files()
        yield
        used_files.reset_used_files()

    def test_records_read_path_for_read_tool(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        assert used_files.get_used_files() == {"READ": ["/etc/hosts"], "WRITE": []}

    def test_records_write_path_for_write_tool(monkeypatch):
        _register(monkeypatch, "CreateFile", "w")
        used_files.record_used_file("CreateFile", {"filepath": "/a.py"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": ["/a.py"]}

    def test_records_both_for_rw_tool(monkeypatch):
        _register(monkeypatch, "ReplaceTextInFile", "rw")
        used_files.record_used_file("ReplaceTextInFile", {"filepath": "/a.py"})
        assert used_files.get_used_files() == {"READ": ["/a.py"], "WRITE": ["/a.py"]}

    def test_execute_only_permission_is_not_tracked(monkeypatch):
        _register(monkeypatch, "RunBashCode", "x")
        used_files.record_used_file("RunBashCode", {"filepath": "/a.sh"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_first_arg_not_filepath_is_ignored(monkeypatch):
        _register(monkeypatch, "SearchText", "r")
        used_files.record_used_file("SearchText", {"query": "x", "filepath": "/a"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_empty_tool_name_is_ignored(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("", {"filepath": "/etc/hosts"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_non_dict_args_is_ignored(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", ["/etc/hosts"])
        used_files.record_used_file("ReadFile", None)
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_empty_args_is_ignored(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_non_string_path_is_ignored(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": 123})
        used_files.record_used_file("ReadFile", {"filepath": None})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_empty_string_path_is_ignored(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": ""})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_unknown_tool_is_ignored(monkeypatch):
        """A tool with no declared permissions adds nothing."""
        monkeypatch.setattr(tools_registry, "_tools_initialized", True)
        used_files.record_used_file("NoSuchTool", {"filepath": "/a.py"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_read_path_is_unique(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/b.py"})
        assert used_files.get_used_files() == {
            "READ": ["/a.py", "/b.py"],
            "WRITE": [],
        }

    def test_write_path_is_unique(monkeypatch):
        _register(monkeypatch, "CreateFile", "w")
        used_files.record_used_file("CreateFile", {"filepath": "/a.py"})
        used_files.record_used_file("CreateFile", {"filepath": "/a.py"})
        assert used_files.get_used_files() == {"READ": [], "WRITE": ["/a.py"]}

    def test_lists_keep_insertion_order(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/first.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/second.py"})
        assert used_files.get_used_files()["READ"] == ["/first.py", "/second.py"]

    def test_get_used_files_returns_a_copy(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        snapshot = used_files.get_used_files()
        # Mutating the snapshot (or its inner list) must not affect the store.
        snapshot["READ"].append("/hacked.py")
        snapshot["WRITE"].append("/hacked.py")
        assert used_files.get_used_files() == {"READ": ["/a.py"], "WRITE": []}

    def test_reset_clears_state(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        assert used_files.get_used_files()["READ"]
        used_files.reset_used_files()
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_format_returns_empty_text_when_nothing_tracked():
        result = used_files.format_used_files()
        assert isinstance(result, Text)
        assert str(result) == ""
        # An empty Text is falsy, so the CLI skips printing the header.
        assert not result

    def test_format_includes_header_and_counts(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        _register(monkeypatch, "CreateFile", "w")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/b.py"})
        used_files.record_used_file("CreateFile", {"filepath": "/a.py"})

        result = used_files.format_used_files()
        text = str(result)

        assert "Used files" in text
        assert "----------" in text
        assert "2 read : /a.py, /b.py" in text
        assert "1 write : /a.py" in text
        # A non-empty report is truthy so the CLI prints it.
        assert result

    def test_format_header_is_styled_cyan(monkeypatch):
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        result = used_files.format_used_files()
        assert any(str(span.style) == "cyan" for span in result.spans)

    def test_format_shows_paths_relative_to_cwd(tmp_path, monkeypatch):
        """Paths under the CWD are printed relative to it (``./file``)."""
        _register(monkeypatch, "ReadFile", "r")
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "subdir"
        sub.mkdir()
        target = sub / "file.py"

        used_files.record_used_file("ReadFile", {"filepath": str(target)})
        text = str(used_files.format_used_files())

        assert "1 read : ./subdir/file.py" in text
        assert str(tmp_path) not in text

    def test_format_keeps_paths_outside_cwd_unchanged(tmp_path, monkeypatch):
        """Paths outside the CWD are left as recorded."""
        _register(monkeypatch, "ReadFile", "r")
        monkeypatch.chdir(tmp_path)
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        text = str(used_files.format_used_files())
        assert "1 read : /etc/hosts" in text

    def test_format_omits_write_line_when_no_writes(monkeypatch):
        """Only reads were tracked: the write line must not appear."""
        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        text = str(used_files.format_used_files())
        assert "1 read : /a.py" in text
        assert "write :" not in text

    def test_format_omits_read_line_when_no_reads(monkeypatch):
        """Only writes were tracked: the read line must not appear."""
        _register(monkeypatch, "CreateFile", "w")
        used_files.record_used_file("CreateFile", {"filepath": "/a.py"})
        text = str(used_files.format_used_files())
        assert "1 write : /a.py" in text
        assert "read :" not in text

    def test_cli_send_prompt_clears_used_files_at_start(monkeypatch):
        """``send_prompt`` must reset the tracker before processing a prompt.

        ``resolve_runtime_config`` is patched to fail immediately so the test
        never reaches the network; the reset happens before that call, so any
        state left over from a previous prompt must already be gone.
        """
        import janito.openai_client.completions_api as client_mod

        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/prev.py"})
        assert used_files.get_used_files()["READ"]

        def boom(*args, **kwargs):
            raise RuntimeError("stop before network")

        monkeypatch.setattr(client_mod, "resolve_runtime_config", boom)
        try:
            client_mod.send_prompt("hello", use_mcp=False)
        except RuntimeError:
            pass
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}

    def test_web_stream_prompt_clears_used_files_at_start(monkeypatch):
        """The web agent loop must also reset the tracker per prompt."""
        import asyncio

        import janito.web.backend.agent.loop as loop_mod
        from janito.web.backend.events import ErrorEvent

        _register(monkeypatch, "ReadFile", "r")
        used_files.record_used_file("ReadFile", {"filepath": "/prev.py"})
        assert used_files.get_used_files()["READ"]

        def boom(*args, **kwargs):
            raise RuntimeError("stop before network")

        monkeypatch.setattr(loop_mod, "resolve_runtime_config", boom)

        class _Cfg:
            model = None
            provider = None
            session_provider = None
            api_type = None

        async def _drain():
            events = []
            async for ev in loop_mod.stream_prompt("hi", [], _Cfg(), use_mcp=False):
                events.append(ev)
            return events

        events = asyncio.run(_drain())
        assert used_files.get_used_files() == {"READ": [], "WRITE": []}
        assert any(isinstance(ev, ErrorEvent) for ev in events)

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                used_files.reset_used_files()
                fn()
                used_files.reset_used_files()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
