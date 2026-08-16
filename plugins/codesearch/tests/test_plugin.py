"""Tests for the codesearch plugin contract (__init__.py, cmd/, on_start)."""

import sys
from pathlib import Path

# Make ``codesearch`` (the plugin package) importable from plugins/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


import codesearch


def test_plugin_contract_symbols():
    """The plugin exposes the full contract (name, on_start, ...)."""
    assert codesearch.name == "codesearch"
    assert callable(codesearch.on_start)
    assert codesearch.SYSTEM_PROMPT == (
        "When searching text on files use the CodeSearch tool before the "
        "other search tools"
    )
    assert isinstance(codesearch.TOOLS, list)
    assert len(codesearch.TOOLS) == 1
    assert isinstance(codesearch.CMD_HANDLERS, list)
    assert len(codesearch.CMD_HANDLERS) == 1


def test_on_start_creates_missing_index(tmp_path, monkeypatch):
    """on_start() creates .janito/codesearch.db when it is missing."""
    (tmp_path / "hello.py").write_text(
        "def hello_world():\n    print('hello world')\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    error = codesearch.on_start()
    assert error is None

    db = tmp_path / ".janito" / "codesearch.db"
    assert db.is_file()

    # The created index is searchable.
    result = codesearch.CodeSearchTool().run(keywords=["hello"], match="and")
    assert result["success"] is True
    assert any(m.startswith("hello.py:") for m in result["matches"])


def test_on_start_skips_when_index_exists(tmp_path, monkeypatch):
    """on_start() is a no-op when .janito/codesearch.db already exists."""
    (tmp_path / ".janito").mkdir()
    db = tmp_path / ".janito" / "codesearch.db"
    db.write_bytes(b"existing")

    monkeypatch.chdir(tmp_path)
    error = codesearch.on_start()

    assert error is None
    # The pre-existing file was left untouched.
    assert db.read_bytes() == b"existing"


def test_codesearch_cmd_handler_registers_and_dispatches(tmp_path, monkeypatch):
    """The CMD_HANDLERS class handles /codesearch update|recreate."""
    handler = codesearch.CMD_HANDLERS[0]()
    assert handler.name == "/codesearch"

    # Other commands are not handled.
    assert handler.handle(None, "/mcp list") is False

    # Unknown subcommand -> handled (returns True) but prints usage.
    assert handler.handle(None, "/codesearch bogus") is True

    # recreate in an empty temp dir builds the index.
    (tmp_path / "hello.py").write_text(
        "def hello_world():\n    pass\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert handler.handle(None, "/codesearch recreate") is True
    assert (tmp_path / ".janito" / "codesearch.db").is_file()

    # update on an existing index is handled.
    assert handler.handle(None, "/codesearch update") is True
