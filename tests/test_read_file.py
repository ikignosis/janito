"""
Tests for the ReadFile tool's line-range handling.

The tool reads a 1-based ``start_line`` and up to ``max_lines`` lines. A
``max_lines`` value that exceeds the number of lines in the file must not
raise an error: the tool clamps it to the last available line and returns
all the lines it could read. The ``head``/``tail`` flags return only the
first/last 10 lines of the file.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.files.read_file import ReadFile


@pytest.fixture
def sample_file(tmp_path):
    """Create a 5-line sample file and return its path."""
    path = tmp_path / "sample.txt"
    path.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def big_file(tmp_path):
    """Create a 25-line sample file and return its path."""
    path = tmp_path / "big.txt"
    path.write_text("".join(f"line {i}\n" for i in range(1, 26)), encoding="utf-8")
    return str(path)


def test_max_lines_beyond_eof_is_clamped(sample_file):
    """A max_lines past the end of the file returns all readable lines, no error."""
    result = ReadFile().run(filepath=sample_file, start_line=1, max_lines=100)

    assert result["success"] is True
    assert result["total_lines"] == 5
    assert result["start_line"] == 1
    assert result["max_lines"] == 100
    assert result["lines_read"] == 5
    assert result["content"] == "line 1\nline 2\nline 3\nline 4\nline 5\n"


def test_max_lines_beyond_eof_with_offset_start(sample_file):
    """Clamping also works when start_line is not 1."""
    result = ReadFile().run(filepath=sample_file, start_line=4, max_lines=100)

    assert result["success"] is True
    assert result["start_line"] == 4
    assert result["lines_read"] == 2
    assert result["content"] == "line 4\nline 5\n"


def test_max_lines_within_range(sample_file):
    """A max_lines inside the range is honoured as-is."""
    result = ReadFile().run(filepath=sample_file, start_line=2, max_lines=2)

    assert result["success"] is True
    assert result["start_line"] == 2
    assert result["lines_read"] == 2
    assert result["content"] == "line 2\nline 3\n"


def test_no_max_lines_reads_to_eof(sample_file):
    """Without max_lines the file is read from start_line to the end."""
    result = ReadFile().run(filepath=sample_file, start_line=2)

    assert result["success"] is True
    assert result["start_line"] == 2
    assert result["max_lines"] is None
    assert result["lines_read"] == 4
    assert result["content"] == "line 2\nline 3\nline 4\nline 5\n"


def test_max_lines_less_than_one_still_errors(sample_file):
    """A max_lines below 1 remains invalid."""
    result = ReadFile().run(filepath=sample_file, start_line=1, max_lines=0)

    assert result["success"] is False
    assert "out of range" in result["error"]


def test_start_line_out_of_range_still_errors(sample_file):
    """An out-of-range start_line is still an error."""
    result = ReadFile().run(filepath=sample_file, start_line=99, max_lines=100)

    assert result["success"] is False
    assert "start_line (99) is out of range" in result["error"]
    assert result["total_lines"] == 5


def test_head_returns_first_ten_lines(big_file):
    """head=True returns exactly the first 10 lines of the file."""
    result = ReadFile().run(filepath=big_file, head=True)

    assert result["success"] is True
    assert result["total_lines"] == 25
    assert result["start_line"] == 1
    assert result["max_lines"] == 10
    assert result["lines_read"] == 10
    assert result["content"] == "".join(f"line {i}\n" for i in range(1, 11))


def test_tail_returns_last_ten_lines(big_file):
    """tail=True returns exactly the last 10 lines of the file."""
    result = ReadFile().run(filepath=big_file, tail=True)

    assert result["success"] is True
    assert result["total_lines"] == 25
    assert result["start_line"] == 16
    assert result["max_lines"] == 10
    assert result["lines_read"] == 10
    assert result["content"] == "".join(f"line {i}\n" for i in range(16, 26))


def test_head_on_small_file_returns_everything(sample_file):
    """head=True on a file with fewer than 10 lines returns the whole file."""
    result = ReadFile().run(filepath=sample_file, head=True)

    assert result["success"] is True
    assert result["start_line"] == 1
    assert result["lines_read"] == 5
    assert result["content"] == "line 1\nline 2\nline 3\nline 4\nline 5\n"


def test_tail_on_small_file_returns_everything(sample_file):
    """tail=True on a file with fewer than 10 lines returns the whole file."""
    result = ReadFile().run(filepath=sample_file, tail=True)

    assert result["success"] is True
    assert result["start_line"] == 1
    assert result["lines_read"] == 5
    assert result["content"] == "line 1\nline 2\nline 3\nline 4\nline 5\n"


def test_head_and_tail_together_still_errors(sample_file):
    """head=True and tail=True at the same time is invalid."""
    result = ReadFile().run(filepath=sample_file, head=True, tail=True)

    assert result["success"] is False
    assert "head and tail cannot both be True" in result["error"]
