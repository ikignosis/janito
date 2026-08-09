"""
Tests for the diff reporting (``report_diff`` in
:mod:`janito.tooling.reporter`), the ``BaseTool.report_diff`` method and the
``ReplaceTextInFile`` integration (the diff is emitted *before* the result).

``report_diff(old_str, new_str)`` builds a unified diff between the two
strings and either prints it to stderr with rich syntax highlighting (CLI
mode) or forwards it to the active report handler as a ``"diff"`` level event
(web mode). ``ReplaceTextInFile`` calls it right before ``report_result``.
"""

import io
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.reporter as reporter
from janito.tooling import BaseTool


class _DummyTool(BaseTool):
    """Minimal concrete BaseTool subclass for tests."""

    def run(self, **kwargs):
        return {"success": True}


if pytest is not None:

    def test_build_diff_produces_unified_diff():
        diff = reporter.build_diff("foo = 1\nbar = 2", "foo = 2\nbar = 2")
        assert "--- before" in diff
        assert "+++ after" in diff
        assert "-foo = 1" in diff
        assert "+foo = 2" in diff
        assert " bar = 2" in diff  # unchanged context line

    def test_build_diff_with_empty_sides():
        assert reporter.build_diff("", "") == ""
        assert reporter.build_diff("a", "a") == ""
        assert "-a" in reporter.build_diff("a", "b")
        assert "+b" in reporter.build_diff("a", "b")

    def test_report_diff_prints_to_stderr(capsys):
        reporter.report_diff("foo = 1", "foo = 2")
        out = capsys.readouterr().err
        assert "--- before" in out
        assert "+++ after" in out
        assert "-foo = 1" in out
        assert "+foo = 2" in out

    def test_diff_theme_gives_removed_lines_red_background():
        # Capture the ANSI output with a truecolor, force-terminal console.
        from rich.console import Console

        buf = io.StringIO()
        orig = reporter._console
        reporter._console = Console(
            width=100, force_terminal=True, color_system="truecolor", file=buf
        )
        try:
            reporter.report_diff("foo = 1", "foo = 2")
        finally:
            reporter._console = orig

        out = buf.getvalue()
        # #3a1414 (dark red) is the DiffTheme background for deleted lines.
        assert "48;2;58;20;20" in out
        assert "-foo = 1" in out

    def test_diff_theme_gives_added_lines_green_background():
        from rich.console import Console

        buf = io.StringIO()
        orig = reporter._console
        reporter._console = Console(
            width=100, force_terminal=True, color_system="truecolor", file=buf
        )
        try:
            reporter.report_diff("foo = 1", "foo = 2")
        finally:
            reporter._console = orig

        out = buf.getvalue()
        # #143214 (dark green) is the DiffTheme background for added lines.
        assert "48;2;20;50;20" in out
        assert "+foo = 2" in out

    def test_diff_theme_styles_removed_and_inserted_tokens():
        from pygments.token import Generic

        style = reporter.DiffTheme.style_for_token(Generic.Deleted)
        assert style["bgcolor"] == "3a1414"
        assert style["color"] == "f8f8f2"
        assert style["bold"] is False

        style = reporter.DiffTheme.style_for_token(Generic.Inserted)
        assert style["bgcolor"] == "143214"
        assert style["color"] == "f8f8f2"
        assert style["bold"] is False

    def test_report_diff_routes_to_handler():
        events = []
        reporter.set_report_handler(
            lambda level, message, end: events.append((level, message, end))
        )
        try:
            reporter.report_diff("a\nb", "a\nc")
        finally:
            reporter.set_report_handler(None)

        assert len(events) == 1
        level, message, end = events[0]
        assert level == "diff"
        assert end == "\n"
        assert "-b" in message
        assert "+c" in message

    def test_base_tool_report_diff_delegates(capsys):
        _DummyTool().report_diff("x = 1", "x = 2")
        out = capsys.readouterr().err
        assert "-x = 1" in out
        assert "+x = 2" in out

    def test_replace_text_in_file_emits_diff_before_result(tmp_path):
        from janito.tools.files.replace_text_in_file import ReplaceTextInFile

        f = tmp_path / "a.py"
        f.write_text("foo = 1\nbar = 2\n", encoding="utf-8")

        events = []
        reporter.set_report_handler(
            lambda level, message, end: events.append((level, message))
        )
        try:
            result = ReplaceTextInFile().run(
                filepath=str(f), old_str="foo = 1", new_str="foo = 2"
            )
        finally:
            reporter.set_report_handler(None)

        assert result["success"] is True
        levels = [level for level, _ in events]
        assert "diff" in levels
        assert "result" in levels
        assert levels.index("diff") < levels.index("result")

        diff_msg = next(message for level, message in events if level == "diff")
        assert "-foo = 1" in diff_msg
        assert "+foo = 2" in diff_msg

    def test_replace_text_in_file_no_diff_on_error(tmp_path):
        from janito.tools.files.replace_text_in_file import ReplaceTextInFile

        f = tmp_path / "a.py"
        f.write_text("foo = 1\n", encoding="utf-8")

        events = []
        reporter.set_report_handler(
            lambda level, message, end: events.append((level, message))
        )
        try:
            result = ReplaceTextInFile().run(
                filepath=str(f), old_str="missing", new_str="x"
            )
        finally:
            reporter.set_report_handler(None)

        assert result["success"] is False
        levels = [level for level, _ in events]
        assert "diff" not in levels
        assert "error" in levels

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                except TypeError:
                    with tempfile.TemporaryDirectory() as d:
                        import os

                        prev = os.getcwd()
                        os.chdir(d)
                        try:
                            fn(Path(d))
                        finally:
                            os.chdir(prev)
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
