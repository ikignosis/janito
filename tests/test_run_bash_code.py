"""
Tests for the system exec tools' output-capping behaviour (issue #49).

The exec tools (RunBashCode, RunPythonCode, RunPythonFile, ...) stream command
output to the screen while the *result dict* carries at most ``MAX_OUTPUT_LINES``
(50) lines of stdout/stderr.  When a stream is longer, a kept temporary file
receives the complete output (streamed in parallel to the screen) and the
result points at it (``stdout_file`` / ``stderr_file`` plus a pointer line
appended to the capped text).  The temp files are removed when the janito
process exits (``atexit``).
"""

import os
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.system import _output_capture as oc
from janito.tools.system._output_capture import (
    MAX_OUTPUT_LINES,
    OutputCapture,
    _cleanup_temp_files,
    build_report_message,
)
from janito.tools.system.run_bash_code import RunBashCode


@pytest.fixture(autouse=True)
def _clean_temp_registry():
    """Ensure no tracked temp files leak between tests."""
    yield
    _cleanup_temp_files()


# ---------------------------------------------------------------------------
# RunBashCode integration tests
# ---------------------------------------------------------------------------


def test_short_output_returned_inline():
    """Output under the cap is returned inline, with no temp files created."""
    tool = RunBashCode()
    result = tool.run(code="echo hello")

    assert result["success"] is True
    assert result["stdout"] == "hello"
    assert result["stderr"] == ""
    assert "stdout_file" not in result
    assert "stderr_file" not in result
    assert oc._TEMP_FILES == set()


def test_long_stdout_capped_and_stored():
    """Output over the cap is capped at 50 lines + a pointer to the full file."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200")

    assert result["success"] is True

    stdout_file = result["stdout_file"]
    assert stdout_file is not None
    assert os.path.isfile(stdout_file)

    # The inline text is exactly the first 50 lines plus a pointer line.
    lines = result["stdout"].split("\n")
    assert lines[0] == "1"
    assert lines[49] == "50"
    assert lines[50] == f"Full stdout available at {stdout_file}"
    assert len(lines) == MAX_OUTPUT_LINES + 1

    # The kept file contains the complete output.
    with open(stdout_file, encoding="utf-8") as fh:
        assert fh.read() == "".join(f"{i}\n" for i in range(1, 201))

    # The file is registered for cleanup on exit.
    assert stdout_file in oc._TEMP_FILES

    # The short stderr stream is not stored.
    assert "stderr_file" not in result
    assert result["stderr"] == ""


def test_long_stderr_capped_and_stored():
    """A long stderr stream is capped and stored in a stderr temp file."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200 >&2")

    assert result["success"] is True

    stderr_file = result["stderr_file"]
    assert stderr_file is not None
    assert os.path.isfile(stderr_file)

    lines = result["stderr"].split("\n")
    assert lines[0] == "1"
    assert lines[49] == "50"
    assert lines[50] == f"Full stderr available at {stderr_file}"
    assert len(lines) == MAX_OUTPUT_LINES + 1

    with open(stderr_file, encoding="utf-8") as fh:
        assert fh.read() == "".join(f"{i}\n" for i in range(1, 201))

    assert stderr_file in oc._TEMP_FILES
    assert "stdout_file" not in result


def test_exactly_max_lines_no_file():
    """Output of exactly MAX_OUTPUT_LINES is returned inline without a file."""
    tool = RunBashCode()
    result = tool.run(code=f"seq 1 {MAX_OUTPUT_LINES}")

    assert result["success"] is True
    assert result["stdout"].count("\n") == MAX_OUTPUT_LINES - 1
    assert result["stdout"].split("\n")[0] == "1"
    assert result["stdout"].split("\n")[-1] == str(MAX_OUTPUT_LINES)
    assert "stdout_file" not in result


def test_both_streams_long_stored():
    """When both streams overflow, both files are created and reported."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 100; seq 1 100 >&2")

    assert result["success"] is True
    assert result["stdout_file"] and result["stderr_file"]
    assert "Full stdout available at" in result["stdout"]
    assert "Full stderr available at" in result["stderr"]


def test_failure_caps_stderr():
    """A failing command with long stderr is capped and still reports an error."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200 >&2; exit 3")

    assert result["success"] is False
    assert result["exit_code"] == 3
    assert result["error"] == "Bash execution failed with exit code 3"
    assert "Full stderr available at" in result["stderr"]
    assert result["stderr_file"] is not None
    assert os.path.isfile(result["stderr_file"])


def test_capture_output_disabled():
    """With capture_output=False there is no stdout key and no temp file."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200", capture_output=False)

    assert result["success"] is True
    assert "stdout" not in result
    assert "stdout_file" not in result
    assert oc._TEMP_FILES == set()


def test_report_result_points_to_stored_files():
    """report_result includes 'Full stdout stored at <tmp>, stderr at <tmp>'."""
    from janito.tooling.reporter import set_report_handler

    captured: list[tuple[str, str]] = []

    def handler(level: str, message: str, end: str) -> None:
        captured.append((level, message))

    set_report_handler(handler)
    try:
        result = RunBashCode().run(code="seq 1 100; seq 1 100 >&2")
    finally:
        set_report_handler(None)

    result_msgs = [m for lvl, m in captured if lvl == "result"]
    assert result_msgs, "expected at least one report_result call"
    assert (
        f"Full stdout stored at {result['stdout_file']}, stderr at {result['stderr_file']}"
        in result_msgs[-1]
    )


def test_cleanup_removes_temp_files():
    """_cleanup_temp_files() deletes every tracked temp file."""
    tool = RunBashCode()
    result = tool.run(code="seq 1 200")
    stdout_file = result["stdout_file"]

    assert os.path.isfile(stdout_file)
    _cleanup_temp_files()
    assert not os.path.exists(stdout_file)
    assert stdout_file not in oc._TEMP_FILES


# ---------------------------------------------------------------------------
# Shared helper unit tests
# ---------------------------------------------------------------------------


def test_output_capture_under_cap_no_file():
    """OutputCapture below the cap produces plain text and no file."""
    cap = OutputCapture("stdout")
    for i in range(10):
        cap.add(str(i))

    text, path = cap.finalize()
    assert text == "\n".join(str(i) for i in range(10))
    assert path is None
    assert cap.line_count() == 10


def test_output_capture_over_cap_creates_file():
    """OutputCapture over the cap creates a kept file with the full output."""
    cap = OutputCapture("stdout")
    for i in range(MAX_OUTPUT_LINES + 10):
        cap.add(str(i))

    text, path = cap.finalize()
    assert path is not None
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == "".join(f"{i}\n" for i in range(MAX_OUTPUT_LINES + 10))

    lines = text.split("\n")
    assert lines[0] == "0"
    assert lines[MAX_OUTPUT_LINES - 1] == str(MAX_OUTPUT_LINES - 1)
    assert lines[MAX_OUTPUT_LINES] == f"Full stdout available at {path}"
    assert len(lines) == MAX_OUTPUT_LINES + 1
    assert path in oc._TEMP_FILES


def test_output_capture_preview():
    """preview() flattens newlines and truncates long streams."""
    cap = OutputCapture("stdout")
    for i in range(200):
        cap.add(str(i))

    preview = cap.preview(10)
    assert preview.startswith("0 1 2 3 4")
    assert preview.endswith("...")

    short = OutputCapture("stderr")
    short.add("boom")
    assert short.preview(100) == "boom"


def test_build_report_message():
    """build_report_message formats the stored-file tail per issue #49."""
    assert build_report_message(None, None) == ""
    assert (
        build_report_message("/tmp/a.txt", None) == "Full stdout stored at /tmp/a.txt"
    )
    assert (
        build_report_message(None, "/tmp/b.txt") == "Full stderr stored at /tmp/b.txt"
    )
    assert build_report_message("/tmp/a.txt", "/tmp/b.txt") == (
        "Full stdout stored at /tmp/a.txt, stderr at /tmp/b.txt"
    )


# ---------------------------------------------------------------------------
# Sibling tools share the behaviour
# ---------------------------------------------------------------------------


def test_run_python_code_shared_behaviour():
    """RunPythonCode caps long stdout and stores the full output."""
    from janito.tools.system.run_python_code import RunPythonCode

    result = RunPythonCode().run(code="[print(i) for i in range(150)]")
    assert result["success"] is True
    assert "Full stdout available at" in result["stdout"]
    assert result["stdout_file"] is not None
    with open(result["stdout_file"], encoding="utf-8") as fh:
        assert fh.read().count("\n") == 150


def test_run_python_file_shared_behaviour(tmp_path):
    """RunPythonFile caps long stdout and stores the full output."""
    from janito.tools.system.run_python_file import RunPythonFile

    script = tmp_path / "many_lines.py"
    script.write_text("for i in range(120):\n    print(i)\n")

    result = RunPythonFile().run(file_path=str(script))
    assert result["success"] is True
    assert "Full stdout available at" in result["stdout"]
    assert result["stdout_file"] is not None
    with open(result["stdout_file"], encoding="utf-8") as fh:
        assert fh.read().count("\n") == 120


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
