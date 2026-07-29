"""
Tests for the in-process used-files tracking.

``janito.tooling.used_files`` records, in memory, every file path touched by a
tool call whose *first* argument is named ``filepath``, together with the names
of the tools that used it. Tracking is deliberately defensive (best-effort and
never raises), so these tests verify both the happy path and that invalid
inputs are silently ignored.

Unlike ``tools_usage`` (SQLite-backed) the state here is a process-global dict,
so every test resets it via ``reset_used_files()``.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.text import Text

import janito.tooling.used_files as used_files

try:
    import pytest
except ImportError:  # pragma: no cover - pytest is a dev dependency
    pytest = None


if pytest is not None:

    @pytest.fixture(autouse=True)
    def _clean_state():
        """Ensure each test starts from (and leaves behind) empty state."""
        used_files.reset_used_files()
        yield
        used_files.reset_used_files()

    def test_records_path_when_first_arg_is_filepath():
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        assert used_files.get_used_files() == {"/etc/hosts": ["ReadFile"]}

    def test_first_arg_not_filepath_is_ignored():
        used_files.record_used_file("SearchText", {"query": "x", "filepath": "/a"})
        assert used_files.get_used_files() == {}

    def test_empty_tool_name_is_ignored():
        used_files.record_used_file("", {"filepath": "/etc/hosts"})
        assert used_files.get_used_files() == {}

    def test_non_dict_args_is_ignored():
        used_files.record_used_file("ReadFile", ["/etc/hosts"])
        used_files.record_used_file("ReadFile", None)
        assert used_files.get_used_files() == {}

    def test_empty_args_is_ignored():
        used_files.record_used_file("ReadFile", {})
        assert used_files.get_used_files() == {}

    def test_non_string_path_is_ignored():
        used_files.record_used_file("ReadFile", {"filepath": 123})
        used_files.record_used_file("ReadFile", {"filepath": None})
        assert used_files.get_used_files() == {}

    def test_empty_string_path_is_ignored():
        used_files.record_used_file("ReadFile", {"filepath": ""})
        assert used_files.get_used_files() == {}

    def test_multiple_tools_on_same_path_accumulate_unique():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("WriteFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        assert used_files.get_used_files() == {"/a.py": ["ReadFile", "WriteFile"]}

    def test_duplicate_tool_name_is_not_recorded_twice():
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        used_files.record_used_file("ReplaceTextInFile", {"filepath": "/etc/hosts"})
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        assert used_files.get_used_files() == {
            "/etc/hosts": ["ReadFile", "ReplaceTextInFile"]
        }

    def test_same_tool_on_different_paths_recorded_per_path():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/b.py"})
        assert used_files.get_used_files() == {
            "/a.py": ["ReadFile"],
            "/b.py": ["ReadFile"],
        }

    def test_multiple_paths_keep_insertion_order():
        used_files.record_used_file("ReadFile", {"filepath": "/first.py"})
        used_files.record_used_file("WriteFile", {"filepath": "/second.py"})
        used = used_files.get_used_files()
        assert list(used.keys()) == ["/first.py", "/second.py"]

    def test_get_used_files_returns_a_copy():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        snapshot = used_files.get_used_files()
        # Mutating the snapshot (or its inner list) must not affect the store.
        snapshot["/a.py"].append("Hacked")
        snapshot["/new.py"] = ["Hacked"]
        assert used_files.get_used_files() == {"/a.py": ["ReadFile"]}

    def test_reset_clears_state():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        assert used_files.get_used_files()
        used_files.reset_used_files()
        assert used_files.get_used_files() == {}

    def test_format_returns_empty_text_when_nothing_tracked():
        result = used_files.format_used_files()
        assert isinstance(result, Text)
        assert str(result) == ""
        # An empty Text is falsy, so the CLI skips printing the header.
        assert not result

    def test_format_includes_header_and_paths():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        used_files.record_used_file("WriteFile", {"filepath": "/a.py"})
        used_files.record_used_file("ReadFile", {"filepath": "/b.py"})

        result = used_files.format_used_files()
        text = str(result)

        assert "===== Used Files =====" in text
        assert "/a.py ReadFile,WriteFile" in text
        assert "/b.py ReadFile" in text
        # A non-empty report is truthy so the CLI prints it.
        assert result

    def test_format_header_is_styled_cyan():
        used_files.record_used_file("ReadFile", {"filepath": "/a.py"})
        result = used_files.format_used_files()
        assert any(str(span.style) == "cyan" for span in result.spans)

    def test_format_shows_paths_relative_to_cwd(tmp_path, monkeypatch):
        """Paths under the CWD are printed relative to it (``./file``)."""
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "subdir"
        sub.mkdir()
        target = sub / "file.py"

        used_files.record_used_file("ReadFile", {"filepath": str(target)})
        text = str(used_files.format_used_files())

        assert "./subdir/file.py ReadFile" in text
        assert str(tmp_path) not in text

    def test_format_keeps_paths_outside_cwd_unchanged(tmp_path, monkeypatch):
        """Paths outside the CWD are left as recorded."""
        monkeypatch.chdir(tmp_path)
        used_files.record_used_file("ReadFile", {"filepath": "/etc/hosts"})
        text = str(used_files.format_used_files())
        assert "/etc/hosts ReadFile" in text

    def test_cli_send_prompt_clears_used_files_at_start(monkeypatch):
        """``send_prompt`` must reset the tracker before processing a prompt.

        ``resolve_runtime_config`` is patched to fail immediately so the test
        never reaches the network; the reset happens before that call, so any
        state left over from a previous prompt must already be gone.
        """
        import janito.openai_client.client as client_mod

        used_files.record_used_file("ReadFile", {"filepath": "/prev.py"})
        assert used_files.get_used_files()

        def boom(*args, **kwargs):
            raise RuntimeError("stop before network")

        monkeypatch.setattr(client_mod, "resolve_runtime_config", boom)
        try:
            client_mod.send_prompt("hello", use_mcp=False)
        except RuntimeError:
            pass
        assert used_files.get_used_files() == {}

    def test_web_stream_prompt_clears_used_files_at_start(monkeypatch):
        """The web agent loop must also reset the tracker per prompt."""
        import asyncio

        import janito.web.backend.agent.loop as loop_mod
        from janito.web.backend.events import ErrorEvent

        used_files.record_used_file("ReadFile", {"filepath": "/prev.py"})
        assert used_files.get_used_files()

        def boom(*args, **kwargs):
            raise RuntimeError("stop before network")

        monkeypatch.setattr(loop_mod, "resolve_runtime_config", boom)

        class _Cfg:
            model = None
            provider = None

        async def _drain():
            events = []
            async for ev in loop_mod.stream_prompt("hi", [], _Cfg(), use_mcp=False):
                events.append(ev)
            return events

        events = asyncio.run(_drain())
        assert used_files.get_used_files() == {}
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
