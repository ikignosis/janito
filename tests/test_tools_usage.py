"""
Tests for the SQLite-backed tool usage tracking.

``janito.tooling.tools_usage`` stores per-tool invocation counters in a
``tools_use.db`` SQLite database inside the Janito config directory. These
tests point the config dir at a temporary directory and verify the database is
created with the expected schema and that counters increment correctly.
"""

import sqlite3
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.tooling.tools_usage as tools_usage


def _point_at(monkeypatch, tmp_path):
    """Point the global config dir at a temp directory and return it."""
    config_dir = tmp_path / "custom_janito"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_dir)
    return config_dir


if pytest is not None:

    def test_db_path_is_in_config_dir(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        assert tools_usage.get_db_path() == config_dir / "tools_use.db"

    def test_record_creates_db_with_expected_schema(monkeypatch, tmp_path):
        config_dir = _point_at(monkeypatch, tmp_path)
        tools_usage.record_tool_use("ReadFile")

        db_path = config_dir / "tools_use.db"
        assert db_path.exists()

        conn = sqlite3.connect(str(db_path))
        try:
            cols = {
                row[1]
                for row in conn.execute("PRAGMA table_info(tools_use)").fetchall()
            }
            assert cols == {"tool_name", "use_count"}
        finally:
            conn.close()

    def test_record_inserts_then_increments(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)

        tools_usage.record_tool_use("ReadFile")
        assert tools_usage.get_tool_use_count("ReadFile") == 1

        tools_usage.record_tool_use("ReadFile")
        tools_usage.record_tool_use("ReadFile")
        assert tools_usage.get_tool_use_count("ReadFile") == 3

    def test_records_multiple_tools_independently(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)

        tools_usage.record_tool_use("ReadFile")
        tools_usage.record_tool_use("ListFiles")
        tools_usage.record_tool_use("ListFiles")

        assert tools_usage.get_tool_use_count("ReadFile") == 1
        assert tools_usage.get_tool_use_count("ListFiles") == 2

    def test_get_all_tool_uses_sorted_by_count(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)

        for _ in range(3):
            tools_usage.record_tool_use("RunBashCode")
        tools_usage.record_tool_use("ReadFile")
        for _ in range(2):
            tools_usage.record_tool_use("ListFiles")

        uses = tools_usage.get_all_tool_uses()
        assert list(uses.keys()) == ["RunBashCode", "ListFiles", "ReadFile"]
        assert uses == {"RunBashCode": 3, "ListFiles": 2, "ReadFile": 1}

    def test_unknown_tool_has_zero_count(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        assert tools_usage.get_tool_use_count("NeverUsed") == 0

    def test_empty_tool_name_is_ignored(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        tools_usage.record_tool_use("")
        assert tools_usage.get_all_tool_uses() == {}

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def setattr(self, obj, name, value):
                setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(_MP(), Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
