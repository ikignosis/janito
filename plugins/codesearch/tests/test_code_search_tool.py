"""Tests for the codesearch plugin tool (plugins/codesearch/tools/code_search).

The tool queries the per-project trigram index at ./.janito/codesearch.db
and is only loaded when that database exists in the current working
directory.
"""

import sys
import time
from pathlib import Path

# Make ``codesearch`` (the plugin package) importable from plugins/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from codesearch import CodeSearch as CodeSearchEngine
from codesearch.index import Index
from codesearch.tools.code_search import CodeSearch


@pytest.fixture()
def project_with_index(tmp_path, monkeypatch):
    """Create a temp project with a code search index and chdir into it."""
    (tmp_path / "hello.py").write_text(
        "def hello_world():\n    print('hello world')\n", encoding="utf-8"
    )
    (tmp_path / "foo.py").write_text("def foo():\n    return 'bar'\n", encoding="utf-8")
    (tmp_path / ".janito").mkdir()

    with CodeSearchEngine(
        str(tmp_path), str(tmp_path / ".janito" / "codesearch.db")
    ) as cs:
        cs.Create()

    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# should_load() gating
# ---------------------------------------------------------------------------


def test_should_load_false_without_index(tmp_path, monkeypatch):
    """should_load() is False when ./.janito/codesearch.db is absent."""
    monkeypatch.chdir(tmp_path)
    assert CodeSearch.should_load() is False
    assert "codesearch.db" in CodeSearch._load_skip_reason


def test_should_load_true_with_index(project_with_index):
    """should_load() is True when ./.janito/codesearch.db exists."""
    assert CodeSearch.should_load() is True


def test_should_load_refreshes_stale_index(project_with_index):
    """A stale index (older than the 1d TTL) is refreshed during load."""
    index_db_path = Path.cwd() / ".janito" / "codesearch.db"

    # Age the recorded last update beyond the TTL.
    with Index(str(index_db_path)) as idx:
        idx.set_last_update(
            {
                "operation": "create",
                "timestamp": "2000-01-01T00:00:00+00:00",
                "timestamp_epoch": time.time() - 2 * 24 * 60 * 60,
                "file_count": 2,
                "trigram_count": 0,
            }
        )

    # Add a file that only an incremental Update() would pick up.
    (Path.cwd() / "fresh.py").write_text(
        "def freshly_added():\n    pass\n", encoding="utf-8"
    )

    assert CodeSearch.should_load() is True

    result = CodeSearch().run(keywords=["freshly_added"], match="and")
    assert result["success"] is True
    assert any(m.startswith("fresh.py:") for m in result["matches"])

    with CodeSearchEngine(str(Path.cwd()), str(index_db_path)) as cs:
        last_modified = cs.last_modified()
    assert last_modified is not None
    assert time.time() - last_modified < 24 * 60 * 60


def test_should_load_skips_refresh_when_fresh(project_with_index):
    """A fresh index (within the TTL) is not refreshed during load."""
    (Path.cwd() / "late.py").write_text(
        "def not_yet_indexed():\n    pass\n", encoding="utf-8"
    )

    assert CodeSearch.should_load() is True

    result = CodeSearch().run(keywords=["not_yet_indexed"], match="and")
    assert result["success"] is True
    assert not any(m.startswith("late.py:") for m in result["matches"])


# ---------------------------------------------------------------------------
# Search behaviour
# ---------------------------------------------------------------------------


def test_run_and(project_with_index):
    """AND search returns lines containing all keywords."""
    result = CodeSearch().run(keywords=["hello", "world"], match="and")

    assert result["success"] is True
    assert result["match"] == "and"
    assert result["matches"] == ["hello.py:2:     print('hello world')"]
    assert result["total_matches"] == 1


def test_run_or(project_with_index):
    """OR search returns lines containing any keyword."""
    result = CodeSearch().run(keywords=["foo", "bar"], match="or")

    assert result["success"] is True
    assert result["match"] == "or"
    assert result["matches"] == [
        "foo.py:1: def foo():",
        "foo.py:2:     return 'bar'",
    ]
    assert result["total_matches"] == 2


def test_run_default_match_is_and(project_with_index):
    """match defaults to 'and' when omitted."""
    result = CodeSearch().run(keywords=["hello", "world"])

    assert result["success"] is True
    assert result["match"] == "and"
    assert result["matches"] == ["hello.py:2:     print('hello world')"]


def test_run_invalid_match(project_with_index):
    """An unsupported match mode returns a structured error."""
    result = CodeSearch().run(keywords=["hello"], match="xor")

    assert result["success"] is False
    assert "error" in result
    assert "xor" in result["error"]


def test_run_missing_index_returns_error(tmp_path, monkeypatch):
    """Searching without an index database returns a structured error."""
    monkeypatch.chdir(tmp_path)
    result = CodeSearch().run(keywords=["hello"], match="and")

    assert result["success"] is False
    assert "error" in result
    # The message points at the plugin flow, not the removed --init-codesearch.
    assert "--init-codesearch" not in result["error"]
    assert "/codesearch recreate" in result["error"]
