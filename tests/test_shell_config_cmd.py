"""Tests for the shell /config command handler."""

from unittest.mock import patch

from janito.shell.cmds.config import _print_config_info


class TestPrintConfigInfo:
    """Tests for _print_config_info context-window display logic."""

    def _run(self, capsys, provider="openai", configured_cw=None, default_cw=128000):
        """Helper: patch config lookups and capture printed output."""
        with (
            patch(
                "janito.shell.cmds.config.get_active_provider",
                return_value=provider,
            ),
            patch(
                "janito.shell.cmds.config.get_api_key",
                return_value="sk-test-key-1234567890",
            ),
            patch(
                "janito.shell.cmds.config.get_masked_api_key",
                return_value="sk-***7890",
            ),
            patch(
                "janito.shell.cmds.config.load_context_window_size",
                return_value=configured_cw,
            ),
            patch(
                "janito.shell.cmds.config.load_endpoint_from_config",
                return_value=None,
            ),
            patch(
                "janito.shell.cmds.config.get_default_context_window_size_from_provider",
                return_value=default_cw,
            ),
        ):
            _print_config_info()
        return capsys.readouterr().out

    def test_explicit_context_window_shown_as_is(self, capsys):
        """When the user has set a context window, display it without suffix."""
        out = self._run(capsys, configured_cw=65536)
        assert "Context Window:     65536" in out
        assert "(default)" not in out

    def test_falls_back_to_provider_default(self, capsys):
        """When not configured, the provider's built-in default is shown with '(default)'."""
        out = self._run(capsys, configured_cw=None, default_cw=128000)
        assert "Context Window:     128000 (default)" in out

    def test_not_set_when_no_default_available(self, capsys):
        """When neither configured nor a provider default exists, show '(not set)'."""
        out = self._run(capsys, configured_cw=None, default_cw=None)
        assert "Context Window:     (not set)" in out
