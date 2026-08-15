"""
Tests for the shared JSON-file store classes (janito.json_store).

Covers the :class:`JsonFileStore` base (path resolution, local-over-global
merge, 0600 permissions, delete-missing-key semantics) and the three
subclasses (:class:`AuthConfigStore`, :class:`SecretsConfigStore`,
:class:`McpConfigStore`).
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
from janito.json_store import (
    AuthConfigStore,
    JsonFileStore,
    McpConfigStore,
    SecretsConfigStore,
)


@pytest.fixture(autouse=True)
def _reset_local_mode():
    """Ensure -l/--local mode never leaks into other test modules."""
    yield
    config_dir_mod.set_local_config_mode(False)


def _point_at(monkeypatch, tmp_path, sub="janito"):
    """Point the base config dir at ``tmp_path/<sub>`` and return it."""
    base = tmp_path / sub
    monkeypatch.setattr(config_dir_mod, "_config_dir", base)
    return base


def _project_cwd(monkeypatch, tmp_path):
    """Chdir to ``tmp_path/project`` so the local dir is ``project/.janito``."""
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    monkeypatch.chdir(project)
    return project


# ----------------------------------------------------------------------
# JsonFileStore base
# ----------------------------------------------------------------------

if pytest is not None:

    def test_base_paths(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("config.json")
        assert store.file_path() == base / "config.json"
        assert store.file_paths() == [base / "config.json"]

    def test_base_file_paths_in_local_mode(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        project = _project_cwd(monkeypatch, tmp_path)
        config_dir_mod.set_local_config_mode(True)
        store = JsonFileStore("config.json")
        assert store.file_path() == project / ".janito" / "config.json"
        assert store.file_paths() == [
            project / ".janito" / "config.json",
            base / "config.json",
        ]

    def test_base_load_missing_returns_default(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("config.json", default={"services": {}})
        assert store.load() == {"services": {}}
        assert store.load() is not store.load()  # fresh copy each time

    def test_base_set_get_delete_roundtrip(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("config.json")
        assert store.set("theme", "dark") is True
        assert store.get("theme") == "dark"
        assert (base / "config.json").exists()
        assert store.delete("theme") is True
        assert store.get("theme") is None
        # Deleting a missing key returns False.
        assert store.delete("theme") is False

    def test_base_list_keys_excludes_metadata(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("config.json")
        store.set("a", 1)
        store.set("provider", "openai")
        assert store.list_keys() == ["a", "provider"]
        assert store.list_keys(exclude={"provider"}) == ["a"]

    def test_base_save_sets_0600_permissions(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("secret.json", chmod_600=True)
        store.save({"k": "v"})
        mode = store.file_path().stat().st_mode & 0o777
        assert mode == 0o600

    def test_base_save_no_chmod_when_disabled(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("plain.json", chmod_600=False)
        store.save({"k": "v"})
        mode = store.file_path().stat().st_mode & 0o777
        assert mode != 0o600

    def test_base_merge_local_wins(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        _project_cwd(monkeypatch, tmp_path)

        # Seed a global value, then a local value that overrides it.
        config_dir_mod.set_local_config_mode(False)
        store = JsonFileStore("config.json")
        store.set("theme", "global")
        store.set("provider", "openai")

        config_dir_mod.set_local_config_mode(True)
        local = JsonFileStore("config.json")
        local.set("theme", "local")

        # Reads merge: local wins for overridden keys, global fills the rest.
        merged = store.load()
        assert merged["theme"] == "local"
        assert merged["provider"] == "openai"

    def test_base_merge_malformed_line_skipped(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = JsonFileStore("config.json")
        store.set("a", 1)
        # Corrupt the file; load must not raise and must return the default.
        store.file_path().write_text("{ not json")
        assert store.load() == {}

    # ------------------------------------------------------------------
    # AuthConfigStore
    # ------------------------------------------------------------------

    def test_auth_store_domain_methods(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = AuthConfigStore()
        assert store.set_api_key("openai", "sk-1") is True
        assert store.get_api_key("openai") == "sk-1"
        assert store.get_api_key("missing") is None
        assert store.list_providers() == ["openai"]
        assert store.delete_api_key("openai") is True
        assert store.delete_api_key("openai") is False
        # The auth file got restrictive permissions.
        mode = (base / "auth.json").stat().st_mode & 0o777
        assert mode == 0o600

    def test_auth_store_does_not_write_provider_key(monkeypatch, tmp_path):
        """Storing an API key never writes the ``provider`` default into auth.json.

        The default provider belongs in config.json; auth.json only holds
        provider -> API key pairs.
        """
        _point_at(monkeypatch, tmp_path)
        store = AuthConfigStore()
        assert store.set_api_key("openai", "sk-1") is True
        config = store.load()
        assert config == {"openai": "sk-1"}
        assert "provider" not in config
        assert store.list_providers() == ["openai"]

    def test_auth_store_local_merge(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        _project_cwd(monkeypatch, tmp_path)

        global_store = AuthConfigStore()
        config_dir_mod.set_local_config_mode(False)
        global_store.set_api_key("openai", "sk-global")

        config_dir_mod.set_local_config_mode(True)
        local_store = AuthConfigStore()
        local_store.set_api_key("openai", "sk-local")
        assert local_store.get_api_key("openai") == "sk-local"
        # A key only present globally still resolves.
        local_store.set_api_key("deepseek", "sk-ds")
        assert global_store.get_api_key("deepseek") == "sk-ds"

    # ------------------------------------------------------------------
    # SecretsConfigStore
    # ------------------------------------------------------------------

    def test_secrets_store_domain_methods(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = SecretsConfigStore()
        assert store.set_secret("token", "abc") is True
        assert store.get_secret("token") == "abc"
        assert store.get_secret("missing") is None
        assert store.list_secrets() == ["token"]
        assert store.secret_exists("token") is True
        assert store.secret_exists("missing") is False
        assert store.delete_secret("token") is True
        assert store.delete_secret("token") is False
        mode = (base / "secrets.json").stat().st_mode & 0o777
        assert mode == 0o600

    # ------------------------------------------------------------------
    # McpConfigStore
    # ------------------------------------------------------------------

    def test_mcp_store_domain_methods(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        store = McpConfigStore()
        # Missing file loads the {"services": {}} default.
        assert store.load() == {"services": {}}
        store.add_service("svc", {"command": "x"})
        assert store.get_service("svc") == {"command": "x"}
        assert store.get_service("missing") is None
        assert store.list_services() == {"svc": {"command": "x"}}
        assert store.remove_service("svc") is True
        assert store.remove_service("svc") is False
        # mcp_services.json is a single file (no local merge) without 0600.
        mode = (base / "mcp_services.json").stat().st_mode & 0o777
        assert mode != 0o600

    def test_mcp_store_load_invalid_json_returns_default(monkeypatch, tmp_path):
        base = _point_at(monkeypatch, tmp_path)
        (base / "mcp_services.json").parent.mkdir(parents=True, exist_ok=True)
        (base / "mcp_services.json").write_text("{ broken")
        store = McpConfigStore()
        assert store.load() == {"services": {}}

    def test_mcp_store_save_roundtrips_json(monkeypatch, tmp_path):
        _point_at(monkeypatch, tmp_path)
        store = McpConfigStore()
        store.save({"services": {"s": {"command": "c"}}})
        raw = json.loads(store.file_path().read_text())
        assert raw == {"services": {"s": {"command": "c"}}}

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

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                with tempfile.TemporaryDirectory() as d:
                    fn(mp, Path(d))
                mp.restore()
                config_dir_mod.set_local_config_mode(False)
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
