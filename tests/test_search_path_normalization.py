"""
Tests that search tools emit cwd-relative paths in their results.

Historically SearchText/SearchRegex interpolated the raw absolute path into
each match line (e.g. ``/abs/path/file.py:3: ...``) while tools like ReadFile,
ListFiles and FindFiles normalise paths relative to the current working
directory (``./file.py``). These tests pin down the consistent behaviour: any
result path that lives under the current working directory must be reported
relative to it (prefixed with ``./``), never as an absolute path.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.files.search_regex import SearchRegex
from janito.tools.files.search_text import SearchText

NEEDLE = "needle_token_xyz"


@pytest.fixture()
def searchable_tree(tmp_path, monkeypatch):
    """Create a small file tree under a temporary cwd and chdir into it."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    target = subdir / "sample.txt"
    target.write_text(f"first line\nsecond {NEEDLE} line\nthird line\n")

    # Make the temp dir the cwd so norm_path() yields './…' relative output.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _assert_relative(match_path: str, cwd: Path) -> None:
    """A result path under cwd must be relative and must not leak the abs path."""
    assert match_path.startswith("./"), f"Expected relative path, got: {match_path}"
    assert str(cwd) not in match_path, f"Absolute cwd leaked into: {match_path}"


def test_search_text_matches_are_relative(searchable_tree):
    result = SearchText().run(paths="subdir", query=NEEDLE)
    assert result["success"]
    assert result["matches"], "expected at least one match"
    for match in result["matches"]:
        path_part = match.split(":", 1)[0]
        _assert_relative(path_part, searchable_tree)
        assert path_part == "./subdir/sample.txt"


def test_search_text_count_only_keys_are_relative(searchable_tree):
    result = SearchText().run(paths="subdir", query=NEEDLE, count_only=True)
    assert result["success"]
    assert result["counts"], "expected at least one counted file"
    for key in result["counts"]:
        _assert_relative(key, searchable_tree)
    assert "./subdir/sample.txt" in result["counts"]


def test_search_regex_matches_are_relative(searchable_tree):
    result = SearchRegex().run(paths="subdir", pattern=r"needle_token_\w+")
    assert result["success"]
    assert result["matches"], "expected at least one match"
    for match in result["matches"]:
        path_part = match.split(":", 1)[0]
        _assert_relative(path_part, searchable_tree)
        assert path_part == "./subdir/sample.txt"


def test_search_regex_count_only_keys_are_relative(searchable_tree):
    result = SearchRegex().run(
        paths="subdir", pattern=r"needle_token_\w+", count_only=True
    )
    assert result["success"]
    assert result["counts"], "expected at least one counted file"
    for key in result["counts"]:
        _assert_relative(key, searchable_tree)
    assert "./subdir/sample.txt" in result["counts"]


def test_search_text_single_file_is_relative(searchable_tree):
    result = SearchText().run(paths="subdir/sample.txt", query=NEEDLE)
    assert result["success"]
    for match in result["matches"]:
        path_part = match.split(":", 1)[0]
        _assert_relative(path_part, searchable_tree)
