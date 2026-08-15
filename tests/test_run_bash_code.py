"""
Tests for the system exec tools' output handling.

The exec tools (RunBashCode, RunPythonCode, RunPythonFile, ...) stream command
output to the screen in real-time and return the *full* captured stdout/stderr
inline in the result dict.  No output is capped and no temp files are written.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.system._streaming import lines_to_text, preview_lines
from janito.tools.system.run_bash_code import RunBashCode

# ---------------------------------------------------------------------------
# RunBashCode integration tests
# ---------------------------------------------------------------------------


def test_short_output_returned_inline():
    """Short output is returned inline."""
    tool = RunBashCode()
    result = tool.run(code="echo hello")

    assert result["success"] is True
    assert result["stdout"] == "hello"
    assert result["stderr"] == ""


def test_long_stdout_returned_inline_uncapped():
    """Long output is returned inline in full, with no temp files."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200")

    assert result["success"] is True

    # Every line is present inline.
    lines = result["stdout"].split("\n")
    assert lines[0] == "1"
    assert lines[49] == "50"
    assert lines[199] == "200"
    assert len(lines) == 200

    # No pointer line, no stored-file keys.
    assert "Full stdout available at" not in result["stdout"]
    assert "stdout_file" not in result
    assert "stderr_file" not in result


def test_long_stderr_returned_inline_uncapped():
    """A long stderr stream is returned inline in full."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200 >&2")

    assert result["success"] is True

    lines = result["stderr"].split("\n")
    assert lines[0] == "1"
    assert lines[49] == "50"
    assert lines[199] == "200"
    assert len(lines) == 200

    assert "Full stderr available at" not in result["stderr"]
    assert "stderr_file" not in result
    assert "stdout_file" not in result


def test_both_streams_returned_inline():
    """Both stdout and stderr are returned inline in full."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 100; seq 1 100 >&2")

    assert result["success"] is True
    assert result["stdout"].split("\n")[-1] == "100"
    assert result["stderr"].split("\n")[-1] == "100"
    assert len(result["stdout"].split("\n")) == 100
    assert len(result["stderr"].split("\n")) == 100
    assert "stdout_file" not in result
    assert "stderr_file" not in result


def test_failure_returns_full_stderr():
    """A failing command returns the full stderr inline and reports an error."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200 >&2; exit 3")

    assert result["success"] is False
    assert result["exit_code"] == 3
    assert result["error"] == "Bash execution failed with exit code 3"
    assert len(result["stderr"].split("\n")) == 200
    assert "stderr_file" not in result


def test_capture_output_disabled():
    """With capture_output=False there is no stdout key."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200", capture_output=False)

    assert result["success"] is True
    assert "stdout" not in result
    assert "stdout_file" not in result


def test_report_result_has_no_stored_files_tail():
    """report_result no longer mentions any stored-file location."""
    from janito.tooling.reporter import set_report_handler

    captured: list[tuple[str, str]] = []

    def handler(level: str, message: str, end: str) -> None:
        captured.append((level, message))

    set_report_handler(handler)
    try:
        RunBashCode().run(code="seq 1 100; seq 1 100 >&2")
    finally:
        set_report_handler(None)

    result_msgs = [m for lvl, m in captured if lvl == "result"]
    assert result_msgs, "expected at least one report_result call"
    assert "stored at" not in result_msgs[-1]


# ---------------------------------------------------------------------------
# Shared helper unit tests
# ---------------------------------------------------------------------------


def test_lines_to_text():
    """lines_to_text strips trailing newlines and joins with a single newline."""
    assert lines_to_text([]) == ""
    assert lines_to_text(["hello\n"]) == "hello"
    assert lines_to_text(["a\n", "b\n", "c\n"]) == "a\nb\nc"
    assert lines_to_text(["a\r\n", "b\n"]) == "a\nb"


def test_preview_lines():
    """preview_lines flattens newlines and truncates long streams."""
    lines = [f"{i}\n" for i in range(200)]
    preview = preview_lines(lines, 10)
    assert preview.startswith("0 1 2 3 4")
    assert preview.endswith("...")

    assert preview_lines(["boom\n"], 100) == "boom"


# ---------------------------------------------------------------------------
# Sibling tools share the behaviour
# ---------------------------------------------------------------------------


def test_run_python_code_shared_behaviour():
    """RunPythonCode returns the full stdout inline."""
    from janito.tools.system.run_python_code import RunPythonCode

    result = RunPythonCode().run(code="[print(i) for i in range(150)]")
    assert result["success"] is True
    assert len(result["stdout"].split("\n")) == 150
    assert result["stdout"].split("\n")[0] == "0"
    assert result["stdout"].split("\n")[-1] == "149"
    assert "stdout_file" not in result


def test_run_python_file_shared_behaviour(tmp_path):
    """RunPythonFile returns the full stdout inline."""
    from janito.tools.system.run_python_file import RunPythonFile

    script = tmp_path / "many_lines.py"
    script.write_text("for i in range(120):\n    print(i)\n")

    result = RunPythonFile().run(file_path=str(script))
    assert result["success"] is True
    assert len(result["stdout"].split("\n")) == 120
    assert "stdout_file" not in result


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
