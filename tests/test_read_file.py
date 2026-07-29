"""
Tests for the ReadFile tool's line-range handling.

In particular, a ``to_line`` value that exceeds the number of lines in the
file must not raise an error: the tool clamps it to the last available line
and returns all the lines it could read.
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


def test_to_line_beyond_eof_is_clamped(sample_file):
    """A to_line past the end of the file returns all readable lines, no error."""
    result = ReadFile().run(filepath=sample_file, from_line=1, to_line=100)

    assert result["success"] is True
    assert result["total_lines"] == 5
    assert result["from_line"] == 1
    assert result["to_line"] == 5
    assert result["lines_read"] == 5
    assert result["content"] == "line 1\nline 2\nline 3\nline 4\nline 5\n"


def test_to_line_beyond_eof_with_offset_start(sample_file):
    """Clamping also works when from_line is not 1."""
    result = ReadFile().run(filepath=sample_file, from_line=4, to_line=100)

    assert result["success"] is True
    assert result["from_line"] == 4
    assert result["to_line"] == 5
    assert result["lines_read"] == 2
    assert result["content"] == "line 4\nline 5\n"


def test_to_line_exactly_at_eof(sample_file):
    """A to_line equal to the number of lines behaves normally."""
    result = ReadFile().run(filepath=sample_file, from_line=1, to_line=5)

    assert result["success"] is True
    assert result["to_line"] == 5
    assert result["lines_read"] == 5


def test_to_line_within_range(sample_file):
    """A to_line inside the range is honoured as-is."""
    result = ReadFile().run(filepath=sample_file, from_line=2, to_line=3)

    assert result["success"] is True
    assert result["from_line"] == 2
    assert result["to_line"] == 3
    assert result["content"] == "line 2\nline 3\n"


def test_to_line_less_than_one_still_errors(sample_file):
    """A to_line below 1 remains invalid."""
    result = ReadFile().run(filepath=sample_file, from_line=1, to_line=0)

    assert result["success"] is False
    assert "out of range" in result["error"]


def test_from_line_out_of_range_still_errors(sample_file):
    """An out-of-range from_line is still an error."""
    result = ReadFile().run(filepath=sample_file, from_line=99, to_line=100)

    assert result["success"] is False
    assert "from_line (99) is out of range" in result["error"]
    assert result["total_lines"] == 5
