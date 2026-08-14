"""
Tests for the ``exclude`` parameter on the file search tools.

SearchText, SearchRegex and FindFiles all accept space-separated glob patterns
to exclude from the results. Excluded directories are pruned (not walked
into), excluded files are skipped, and single-file roots are matched against
their basename.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.files.find_files import FindFiles
from janito.tools.files.search_regex import SearchRegex
from janito.tools.files.search_text import SearchText


@pytest.fixture
def search_tree(tmp_path, monkeypatch):
    """A small file tree with a directory to exclude."""
    (tmp_path / "keep").mkdir()
    (tmp_path / "skip").mkdir()
    (tmp_path / "keep" / "a.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "skip" / "b.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "top.txt").write_text("needle\n", encoding="utf-8")
    # The tools load ignore specs from the current working directory.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _match_paths(matches):
    """Extract file paths from a list of 'filepath:lineno: content' matches."""
    return {Path(m.split(":")[0]).name for m in matches}


# ---- SearchText ----


def test_search_text_report_start_shows_exclude(search_tree, capsys):
    SearchText().run(paths=".", query="needle", exclude="skip")

    err = " ".join(capsys.readouterr().err.split())
    assert "exclude 'skip'" in err


def test_search_text_excludes_directory(search_tree):
    result = SearchText().run(paths=".", query="needle", exclude="skip")

    assert result["success"] is True
    assert _match_paths(result["matches"]) == {"a.txt", "top.txt"}


def test_search_text_excludes_by_basename_pattern(search_tree):
    result = SearchText().run(paths=".", query="needle", exclude="*.txt")

    assert result["success"] is True
    assert result["matches"] == []


def test_search_text_excludes_single_file_root(search_tree):
    result = SearchText().run(paths="top.txt", query="needle", exclude="top.txt")

    assert result["success"] is True
    assert result["matches"] == []


def test_search_text_count_only_respects_exclude(search_tree):
    result = SearchText().run(
        paths=".", query="needle", count_only=True, exclude="skip"
    )

    assert result["success"] is True
    assert {Path(k).name for k in result["counts"]} == {"a.txt", "top.txt"}


# ---- SearchRegex ----


def test_search_regex_report_start_shows_exclude(search_tree, capsys):
    SearchRegex().run(paths=".", pattern="needle", exclude="skip")

    err = " ".join(capsys.readouterr().err.split())
    assert "exclude 'skip'" in err


def test_search_regex_excludes_directory(search_tree):
    result = SearchRegex().run(paths=".", pattern="needle", exclude="skip")

    assert result["success"] is True
    assert _match_paths(result["matches"]) == {"a.txt", "top.txt"}


def test_search_regex_excludes_by_basename_pattern(search_tree):
    result = SearchRegex().run(paths=".", pattern="needle", exclude="*.txt")

    assert result["success"] is True
    assert result["matches"] == []


def test_search_regex_excludes_single_file_root(search_tree):
    result = SearchRegex().run(paths="top.txt", pattern="needle", exclude="top.txt")

    assert result["success"] is True
    assert result["matches"] == []


def test_search_regex_count_only_respects_exclude(search_tree):
    result = SearchRegex().run(
        paths=".", pattern="needle", count_only=True, exclude="skip"
    )

    assert result["success"] is True
    assert {Path(k).name for k in result["counts"]} == {"a.txt", "top.txt"}


# ---- FindFiles ----


def test_find_files_report_start_shows_exclude(search_tree, capsys):
    FindFiles().run(paths=".", pattern="*.txt", exclude="skip")

    err = " ".join(capsys.readouterr().err.split())
    assert "exclude 'skip'" in err


def test_find_files_excludes_directory(search_tree):
    result = FindFiles().run(paths=".", pattern="*.txt", exclude="skip")

    assert result["success"] is True
    assert set(result["files"]) == {"keep/a.txt", "top.txt"}


def test_find_files_excludes_directory_glob(search_tree):
    result = FindFiles().run(paths=".", pattern="*.txt", exclude="skip/*")

    assert result["success"] is True
    assert set(result["files"]) == {"keep/a.txt", "top.txt"}


def test_find_files_excludes_single_file(search_tree):
    result = FindFiles().run(paths=".", pattern="*.txt", exclude="top.txt")

    assert result["success"] is True
    assert set(result["files"]) == {"keep/a.txt", "skip/b.txt"}


def test_find_files_multiple_exclude_patterns(search_tree):
    result = FindFiles().run(paths=".", pattern="*.txt", exclude="skip keep")

    assert result["success"] is True
    assert set(result["files"]) == {"top.txt"}


# ---- Exclude + gitignore interplay ----


def test_exclude_still_prunes_with_gitignore_disabled(tmp_path, monkeypatch):
    """exclude works independently of respect_gitignore."""
    (tmp_path / "keep").mkdir()
    (tmp_path / "skip").mkdir()
    (tmp_path / "keep" / "a.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "skip" / "b.txt").write_text("needle\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = SearchText().run(
        paths=".", query="needle", exclude="skip", respect_gitignore=False
    )

    assert result["success"] is True
    assert _match_paths(result["matches"]) == {"a.txt"}
