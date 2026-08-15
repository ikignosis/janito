"""
Tests for the overwrite-confirmation behaviour of ``--set-api-key``.

When an API key is already stored for a provider, ``handle_set_api_key`` must
warn the user and ask for confirmation before overwriting it. The ``--force``
flag bypasses the prompt, and when stdin is not interactive the overwrite is
refused unless ``--force`` is supplied.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.auth_config as ac
import janito.config_dir as config_dir_mod
from janito.cli.handlers.auth import handle_set_api_key


class _FakeStdin:
    """Minimal stand-in for sys.stdin with a controllable isatty()."""

    def __init__(self, tty: bool = True):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary, isolated directory."""
    config_dir = tmp_path / ".janito"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_dir)
    return config_dir


def _args(provider="openai", key="sk-new", force=False):
    return SimpleNamespace(provider=provider, set_api_key=key, force=force)


if pytest is not None:

    def test_new_provider_stores_without_prompt(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))

        called = {"input": False}

        def _fail_input(*a, **k):
            called["input"] = True
            raise AssertionError("input() should not be called for a new provider")

        monkeypatch.setattr("builtins.input", _fail_input)

        rc = handle_set_api_key(_args(key="sk-first"))
        assert rc == 0
        assert ac.get_api_key("openai") == "sk-first"
        assert called["input"] is False

    def test_set_api_key_does_not_write_default_provider(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))

        rc = handle_set_api_key(_args(key="sk-first"))
        assert rc == 0
        # The default provider belongs in config.json; auth.json only holds
        # provider -> API key pairs, never a "provider" metadata key.
        assert ac.get_api_key("openai") == "sk-first"
        config = ac.load_auth_config()
        assert "provider" not in config
        assert config == {"openai": "sk-first"}

    def test_existing_key_confirmed_overwrites(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
        monkeypatch.setattr("builtins.input", lambda *a, **k: "y")

        rc = handle_set_api_key(_args(key="sk-new"))
        assert rc == 0
        assert ac.get_api_key("openai") == "sk-new"
        # A warning must be shown before overwriting.
        assert "already" in capsys.readouterr().err

    def test_existing_key_declined_keeps_old(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
        monkeypatch.setattr("builtins.input", lambda *a, **k: "n")

        rc = handle_set_api_key(_args(key="sk-new"))
        assert rc == 1
        # The existing key must be preserved.
        assert ac.get_api_key("openai") == "sk-old"

    def test_existing_key_empty_answer_defaults_to_no(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
        monkeypatch.setattr("builtins.input", lambda *a, **k: "")

        rc = handle_set_api_key(_args(key="sk-new"))
        assert rc == 1
        assert ac.get_api_key("openai") == "sk-old"

    def test_force_overwrites_without_prompt(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))

        def _fail_input(*a, **k):
            raise AssertionError("input() should not be called when --force is used")

        monkeypatch.setattr("builtins.input", _fail_input)

        rc = handle_set_api_key(_args(key="sk-new", force=True))
        assert rc == 0
        assert ac.get_api_key("openai") == "sk-new"

    def test_non_interactive_without_force_is_refused(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=False))

        def _fail_input(*a, **k):
            raise AssertionError("input() should not be called when not a tty")

        monkeypatch.setattr("builtins.input", _fail_input)

        rc = handle_set_api_key(_args(key="sk-new"))
        assert rc == 1
        # Must not overwrite and must hint at --force.
        assert ac.get_api_key("openai") == "sk-old"
        assert "--force" in capsys.readouterr().err

    def test_non_interactive_with_force_overwrites(monkeypatch, tmp_path):
        _use_temp_config(monkeypatch, tmp_path)
        ac.set_api_key("openai", "sk-old")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=False))

        rc = handle_set_api_key(_args(key="sk-new", force=True))
        assert rc == 0
        assert ac.get_api_key("openai") == "sk-new"

    def test_missing_provider_errors(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        rc = handle_set_api_key(_args(provider=None))
        assert rc == 1
        assert "no default provider" in capsys.readouterr().err

    def test_falls_back_to_config_provider(monkeypatch, tmp_path, capsys):
        _use_temp_config(monkeypatch, tmp_path)
        # A default provider configured via --set provider=<name> (config.json).
        import janito.config_store as gc

        gc.set_config_value("provider", "alibaba")
        monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))

        rc = handle_set_api_key(_args(provider=None, key="sk-cfg"))
        assert rc == 0
        # The key must be stored for the configured provider.
        assert ac.get_api_key("alibaba") == "sk-cfg"
        assert ac.get_api_key("openai") is None
        assert "Using configured provider 'alibaba'" in capsys.readouterr().out

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        class _Cap:
            def readouterr(self):
                return SimpleNamespace(out="", err="")

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                with tempfile.TemporaryDirectory() as d:
                    try:
                        fn(mp, Path(d), _Cap())
                    except TypeError:
                        fn(mp, Path(d))
                mp.restore()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
