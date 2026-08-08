"""
Tests for the tracker classes introduced in Phase 3:

- ``ChangesTracker`` (janito.tooling.changes)
- ``UsedFilesTracker`` (janito.tooling.used_files)
- ``ToolUsageStore`` (janito.tooling.tools_usage)

Behavioural equivalence with the module-level functions is covered by the
existing tests (test_changes / test_used_files / test_tools_usage), which
exercise the module functions.  These tests pin the class contract and the
per-instance state guarantees.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.tooling.changes as changes_mod
import janito.tooling.tools_usage as tools_usage_mod
import janito.tooling.used_files as used_files_mod


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    """Isolate cwd and the process-global used-files tracker."""
    monkeypatch.chdir(tmp_path)
    used_files_mod.reset_used_files()
    yield
    used_files_mod.reset_used_files()


if pytest is not None:
    # ---- ChangesTracker ------------------------------------------------

    def test_changes_tracker_roundtrip(tmp_path):
        tracker = changes_mod.ChangesTracker()
        assert tracker.file_path() == tmp_path / ".janito" / "changes.jsonl"

        tracker.record("CreateFile", {"filepath": "a.py", "content": "x"})
        assert tracker.load() == [
            {"tool": "CreateFile", "params": {"filepath": "a.py", "content": "x"}}
        ]
        assert tracker.clear() is True
        assert tracker.load() == []
        assert tracker.clear() is False

    def test_changes_tracker_ignores_non_write_tools():
        tracker = changes_mod.ChangesTracker()
        # Read-only tools with a filepath first arg are not recorded.
        tracker.record("ReadFile", {"filepath": "a.py"})
        assert tracker.load() == []

    def test_changes_module_functions_delegate():
        tracker = changes_mod.ChangesTracker()
        tracker.record("CreateFile", {"filepath": "a.py", "content": "x"})
        assert changes_mod.load_changes() == tracker.load()
        assert changes_mod.get_changes_file_path() == tracker.file_path()
        assert changes_mod.clear_changes() is True
        assert tracker.load() == []

    # ---- UsedFilesTracker ----------------------------------------------

    def test_used_files_tracker_per_instance_isolation():
        t1 = used_files_mod.UsedFilesTracker()
        t2 = used_files_mod.UsedFilesTracker()

        # Both share the same module-level permissions registry, so we inject
        # a fake tool with permissions for the duration.
        import janito.tooling.tools_registry as tools_registry

        class _Pinned:
            def __enter__(self):
                self._init = tools_registry._tools_initialized
                tools_registry._tools_initialized = True
                fake = lambda **kwargs: {"success": True}  # noqa: E731
                fake._tool_permissions = "r"
                self._prev = tools_registry.AVAILABLE_TOOLS.get("FakeRead")
                tools_registry.AVAILABLE_TOOLS["FakeRead"] = fake

            def __exit__(self, *exc):
                tools_registry._tools_initialized = self._init
                if self._prev is None:
                    tools_registry.AVAILABLE_TOOLS.pop("FakeRead", None)
                else:
                    tools_registry.AVAILABLE_TOOLS["FakeRead"] = self._prev

        with _Pinned():
            t1.record("FakeRead", {"filepath": "/a.py"})
        assert t1.snapshot() == {"READ": ["/a.py"], "WRITE": []}
        # t2 was never recorded to -> empty.
        assert t2.snapshot() == {"READ": [], "WRITE": []}

    def test_used_files_tracker_reset_and_format(tmp_path, monkeypatch):
        import janito.tooling.tools_registry as tools_registry

        monkeypatch.setattr(tools_registry, "_tools_initialized", True)
        fake = lambda **kwargs: {"success": True}  # noqa: E731
        fake._tool_permissions = "r"
        monkeypatch.setitem(tools_registry.AVAILABLE_TOOLS, "FakeRead", fake)

        tracker = used_files_mod.UsedFilesTracker()
        target = tmp_path / "subdir" / "file.py"
        target.parent.mkdir(parents=True)
        tracker.record("FakeRead", {"filepath": str(target)})

        text = str(tracker.format())
        assert "1 read : ./subdir/file.py" in text

        tracker.reset()
        assert tracker.snapshot() == {"READ": [], "WRITE": []}
        assert str(tracker.format()) == ""

    def test_used_files_module_functions_delegate(tmp_path, monkeypatch):
        import janito.tooling.tools_registry as tools_registry

        monkeypatch.setattr(tools_registry, "_tools_initialized", True)
        fake = lambda **kwargs: {"success": True}  # noqa: E731
        fake._tool_permissions = "r"
        monkeypatch.setitem(tools_registry.AVAILABLE_TOOLS, "FakeRead", fake)

        # The module functions operate on the module singleton.
        used_files_mod.record_used_file("FakeRead", {"filepath": "/a.py"})
        assert used_files_mod.get_used_files() == used_files_mod._tracker.snapshot()
        assert used_files_mod.get_used_files() == {"READ": ["/a.py"], "WRITE": []}

        used_files_mod.reset_used_files()
        assert used_files_mod._tracker.snapshot() == {"READ": [], "WRITE": []}

    # ---- ToolUsageStore ------------------------------------------------

    def test_tool_usage_store_explicit_db_path(tmp_path):
        store = tools_usage_mod.ToolUsageStore(db_path=tmp_path / "custom.db")
        assert store.db_path == tmp_path / "custom.db"
        store.record_use("ReadFile")
        store.record_use("ReadFile")
        assert store.use_count("ReadFile") == 2
        assert store.all_uses() == {"ReadFile": 2}

    def test_tool_usage_store_default_db_path(monkeypatch, tmp_path):
        import janito.config_dir as config_dir_mod

        config_dir = tmp_path / "janito"
        monkeypatch.setattr(config_dir_mod, "_config_dir", config_dir)
        store = tools_usage_mod.ToolUsageStore()
        assert store.db_path == config_dir / "tools_use.db"

    def test_tool_usage_store_per_instance_isolation(tmp_path):
        store_a = tools_usage_mod.ToolUsageStore(db_path=tmp_path / "a.db")
        store_b = tools_usage_mod.ToolUsageStore(db_path=tmp_path / "b.db")
        store_a.record_use("ListFiles")
        assert store_a.use_count("ListFiles") == 1
        assert store_b.use_count("ListFiles") == 0
        assert store_b.all_uses() == {}

    def test_tool_usage_module_functions_delegate(monkeypatch, tmp_path):
        import janito.config_dir as config_dir_mod

        monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
        tools_usage_mod.record_tool_use("ReadFile")
        store = tools_usage_mod.ToolUsageStore()
        assert tools_usage_mod.get_tool_use_count("ReadFile") == store.use_count(
            "ReadFile"
        )
        assert tools_usage_mod.get_all_tool_uses() == store.all_uses()
        assert tools_usage_mod.get_db_path() == store.db_path

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def chdir(self, path):
                import os

                self._undo.append((os, "getcwd", os.getcwd()))
                os.chdir(path)

            def setitem(self, obj, name, value):
                self.setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    if value is None:
                        continue
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                try:
                    with tempfile.TemporaryDirectory() as d:
                        fn(mp, Path(d))
                finally:
                    mp.restore()
                    used_files_mod.reset_used_files()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
