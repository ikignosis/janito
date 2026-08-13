"""
Tests for .janitoignore support in the file tools.

.janitoignore must behave like .gitignore on the tools, with the exception
that ``respect_gitignore`` does not apply to it: .janitoignore patterns are
always respected, even when ``respect_gitignore=False`` (or the
``--no-gitignore`` CLI flag is used).

The .janitoignore file itself is automatically added to the ignore list, so
it never appears in listings, finds or search results.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.tools.files.find_files import FindFiles
from janito.tools.files.list_files import ListFiles
from janito.tools.files.search_regex import SearchRegex
from janito.tools.files.search_text import SearchText


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """A directory with .janitoignore, .gitignore and sample files."""
    (tmp_path / ".janitoignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("gitignored.txt\n", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "gitignored.txt").write_text("needle\n", encoding="utf-8")
    # The tools load ignore specs from the current working directory.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _basenames(paths):
    """Extract basenames from a list of returned paths."""
    return {Path(p).name for p in paths}


# ── ListFiles ──────────────────────────────────────────────────────────


def test_list_files_always_respects_janitoignore(project_dir):
    """ignored.txt is excluded even when respect_gitignore=False."""
    result = ListFiles().run(directory=".", respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(result["files"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names  # .janitoignore always respected
    assert "gitignored.txt" in names  # .gitignore NOT respected
    assert ".janitoignore" not in names  # the file itself is auto-ignored
    assert result["janitoignore_applied"] is True
    assert result["gitignore_applied"] is False
    assert result["stats"]["janitoignore_ignored"] == 2  # .janitoignore + ignored.txt
    assert result["stats"]["gitignore_ignored"] == 0


def test_list_files_respects_both_when_gitignore_enabled(project_dir):
    """With respect_gitignore=True both ignore files apply."""
    result = ListFiles().run(directory=".", respect_gitignore=True)

    assert result["success"] is True
    names = _basenames(result["files"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names
    assert "gitignored.txt" not in names
    assert ".janitoignore" not in names  # the file itself is auto-ignored
    assert result["janitoignore_applied"] is True
    assert result["gitignore_applied"] is True
    assert result["stats"]["janitoignore_ignored"] == 2  # .janitoignore + ignored.txt
    assert result["stats"]["gitignore_ignored"] == 1


def test_list_files_recursive_prunes_janitoignored_directory(project_dir):
    """A directory listed in .janitoignore is not walked into."""
    (project_dir / "secret").mkdir()
    (project_dir / "secret" / "hidden.txt").write_text("needle\n", encoding="utf-8")
    (project_dir / ".janitoignore").write_text("secret/\n", encoding="utf-8")

    result = ListFiles().run(directory=".", recursive=True, respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(result["files"])
    assert "hidden.txt" not in names
    assert "secret" not in names
    assert ".janitoignore" not in names  # the file itself is auto-ignored
    assert result["stats"]["janitoignore_ignored"] == 2  # .janitoignore + secret/


# ── FindFiles ──────────────────────────────────────────────────────────


def test_find_files_always_respects_janitoignore(project_dir):
    """FindFiles skips .janitoignore'd entries even without gitignore."""
    result = FindFiles().run(paths=".", respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(result["files"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names
    assert "gitignored.txt" in names
    assert ".janitoignore" not in names  # the file itself is auto-ignored
    assert result["stats"]["janitoignore_ignored"] == 2  # .janitoignore + ignored.txt
    assert result["stats"]["gitignore_ignored"] == 0


def test_find_files_respects_both_when_gitignore_enabled(project_dir):
    """With respect_gitignore=True both ignore files apply."""
    result = FindFiles().run(paths=".", respect_gitignore=True)

    assert result["success"] is True
    names = _basenames(result["files"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names
    assert "gitignored.txt" not in names
    assert ".janitoignore" not in names  # the file itself is auto-ignored
    assert result["stats"]["janitoignore_ignored"] == 2  # .janitoignore + ignored.txt
    assert result["stats"]["gitignore_ignored"] == 1


# ── SearchText ─────────────────────────────────────────────────────────


def test_search_text_skips_janitoignore_files(project_dir):
    """SearchText does not return matches from .janitoignore'd files."""
    result = SearchText().run(paths=".", query="needle", respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(m.split(":")[0] for m in result["matches"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names
    assert "gitignored.txt" in names
    assert result["files_ignored_by_janitoignore"] == 2  # .janitoignore + ignored.txt
    assert result["files_ignored_by_gitignore"] == 0


def test_search_text_count_only_skips_janitoignore_files(project_dir):
    """count_only mode also respects .janitoignore."""
    result = SearchText().run(
        paths=".", query="needle", count_only=True, respect_gitignore=False
    )

    assert result["success"] is True
    counted_names = _basenames(result["counts"].keys())
    assert "visible.txt" in counted_names
    assert "ignored.txt" not in counted_names
    assert "gitignored.txt" in counted_names


# ── SearchRegex ────────────────────────────────────────────────────────


def test_search_regex_skips_janitoignore_files(project_dir):
    """SearchRegex does not return matches from .janitoignore'd files."""
    result = SearchRegex().run(paths=".", pattern="needle", respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(m.split(":")[0] for m in result["matches"])
    assert "visible.txt" in names
    assert "ignored.txt" not in names
    assert "gitignored.txt" in names
    assert result["files_ignored_by_janitoignore"] == 2  # .janitoignore + ignored.txt
    assert result["files_ignored_by_gitignore"] == 0


def test_search_regex_skips_janitoignored_directory(project_dir):
    """Directories listed in .janitoignore are not searched."""
    (project_dir / "secret").mkdir()
    (project_dir / "secret" / "hidden.txt").write_text("needle\n", encoding="utf-8")
    (project_dir / ".janitoignore").write_text("secret/\n", encoding="utf-8")

    result = SearchRegex().run(paths=".", pattern="needle", respect_gitignore=False)

    assert result["success"] is True
    names = _basenames(m.split(":")[0] for m in result["matches"])
    assert "visible.txt" in names
    assert "hidden.txt" not in names
    assert "secret" not in names


# ---------------------------------------------------------------------------
# The .janitoignore file itself is always ignored
# ---------------------------------------------------------------------------


def test_janitoignore_file_itself_auto_ignored(project_dir):
    """The .janitoignore file never appears, even with no matching patterns."""
    # Content matches the search query below, so any result would show it.
    (project_dir / ".janitoignore").write_text("needle\n", encoding="utf-8")

    listed = _basenames(
        ListFiles().run(directory=".", respect_gitignore=False)["files"]
    )
    assert ".janitoignore" not in listed

    found = _basenames(
        FindFiles().run(paths=".", pattern=".janitoignore", respect_gitignore=False)[
            "files"
        ]
    )
    assert ".janitoignore" not in found

    searched = _basenames(
        m.split(":")[0]
        for m in SearchText().run(paths=".", query="needle", respect_gitignore=False)[
            "matches"
        ]
    )
    assert "visible.txt" in searched
    assert ".janitoignore" not in searched
