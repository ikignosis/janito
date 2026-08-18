"""
Tests for the /plugins shell command.

The shell command lists the plugins installed in the plugins directory
(<config_dir>/plugins, default ~/.janito/plugins) using
janito.plugin_manager.scan_installed_plugins, showing each plugin's name,
path and load status for the current session. These tests verify the
command is registered, dispatches correctly, and renders the expected
output for populated and empty plugin sets.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import pytest

import janito.shell.cmds.plugins as plugins_cmd
from janito.plugin_manager import Plugin
from janito.shell.cmds.plugins import PluginsCmdHandler


def _clean(text: str) -> str:
    """Strip whitespace, punctuation and rich table border characters,
    keeping word characters and hyphens."""
    import re

    return re.sub(r"[^\w-]+", "", text)


def _run_handler(installed, loaded=None, plugins_dir=None, user_input="/plugins"):
    """Run the /plugins handler with patched plugin data, capturing output."""
    import io

    if loaded is None:
        loaded = []
    if plugins_dir is None:
        plugins_dir = Path("/tmp/.janito/plugins")

    handler = PluginsCmdHandler()
    output = io.StringIO()
    with patch("sys.stdout", output), patch.object(
        plugins_cmd, "scan_installed_plugins", return_value=installed
    ), patch.object(plugins_cmd, "LOADED_PLUGINS", loaded), patch.object(
        plugins_cmd, "get_default_plugins_dir", return_value=plugins_dir
    ):
        handled = handler.handle(object(), user_input)
    return handled, output.getvalue()


if pytest is not None:

    def test_plugins_command_is_registered():
        from janito.shell.cmds import get_registered_commands

        names = [c.name for c in get_registered_commands()]
        assert "/plugins" in names

    def test_handler_name():
        assert PluginsCmdHandler().name == "/plugins"

    def test_handle_dispatches_only_exact_command():
        handler = PluginsCmdHandler()
        assert handler.handle(object(), "/plugins") is True
        assert handler.handle(object(), "/PLUGINS") is True
        assert handler.handle(object(), "  /plugins  ") is True
        assert handler.handle(object(), "/plugins extra") is False
        assert handler.handle(object(), "/tools") is False

    def test_lists_installed_plugins(tmp_path):
        plugins_dir = tmp_path / ".janito" / "plugins"
        installed = [
            ("codesearch", plugins_dir / "janito-codesearch-plugin"),
            ("gmail", plugins_dir / "janito-gmail-plugin"),
        ]
        loaded = [
            Plugin(
                name="codesearch",
                path=plugins_dir / "janito-codesearch-plugin",
                load_error=None,
            )
        ]

        handled, output = _run_handler(
            installed, loaded=loaded, plugins_dir=plugins_dir
        )

        assert handled is True
        assert "codesearch" in output
        assert "gmail" in output
        # The Path column may wrap long paths across lines with table border
        # characters between the fragments, so strip all non-word characters
        # before asserting on the full directory name.
        clean = _clean(output)
        assert "janito-codesearch-plugin" in clean
        assert "Loaded" in output
        assert "Not loaded" in output
        assert _clean(str(plugins_dir)) in clean

    def test_shows_load_error(tmp_path):
        plugins_dir = tmp_path / "plugins"
        path = plugins_dir / "broken-plugin"
        installed = [("broken", path)]
        loaded = [Plugin(name="broken", path=path, load_error="index build failed")]

        _, output = _run_handler(installed, loaded=loaded, plugins_dir=plugins_dir)

        assert "ERROR: index build failed" in output

    def test_empty_output_shows_helpful_message(tmp_path):
        plugins_dir = tmp_path / "empty" / "plugins"
        handled, output = _run_handler([], plugins_dir=plugins_dir)

        assert handled is True
        assert "No plugins installed." in output
        assert "--install-plugin" in output
        # The Plugins dir row may wrap, so strip all non-word characters
        # before asserting on the full directory.
        assert _clean(str(plugins_dir)) in _clean(output)

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with tempfile.TemporaryDirectory() as d:
                    fn(Path(d))
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
