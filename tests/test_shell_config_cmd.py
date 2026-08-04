"""Tests for the shell /show_config command handler."""

from unittest.mock import patch

from janito.shell.cmds.show_config import _print_config_info


class TestPrintConfigInfo:
    """Tests for _print_config_info max-output-tokens display logic."""

    def _run(
        self,
        capsys,
        provider=None,
        configured_max_tokens=None,
        default_max_tokens=128000,
    ):
        """Helper: patch config lookups and capture printed output.

        Args:
            provider: The session provider to pass to ``_print_config_info``.
                When None, the (patched) configured default is used.
        """
        with (
            patch(
                "janito.shell.cmds.show_config.get_active_provider",
                return_value="openai",
            ),
            patch(
                "janito.shell.cmds.show_config.get_api_key",
                return_value="sk-test-key-1234567890",
            ),
            patch(
                "janito.shell.cmds.show_config.get_masked_api_key",
                return_value="sk-***7890",
            ),
            patch(
                "janito.shell.cmds.show_config.load_max_output_tokens",
                return_value=configured_max_tokens,
            ),
            patch(
                "janito.shell.cmds.show_config.load_endpoint_from_config",
                return_value=None,
            ),
            patch(
                "janito.shell.cmds.show_config.get_default_max_output_tokens_from_provider",
                return_value=default_max_tokens,
            ),
        ):
            _print_config_info(provider)
        return capsys.readouterr().out

    def test_explicit_max_output_tokens_shown_as_is(self, capsys):
        """When the user has set max output tokens, display them without suffix."""
        out = self._run(capsys, configured_max_tokens=65536)
        assert "Max Output Tokens:  65536" in out
        assert "(default)" not in out

    def test_falls_back_to_provider_default(self, capsys):
        """When not configured, the provider's built-in default is shown with '(default)'."""
        out = self._run(capsys, configured_max_tokens=None, default_max_tokens=128000)
        assert "Max Output Tokens:  128000 (default)" in out

    def test_not_set_when_no_default_available(self, capsys):
        """When neither configured nor a provider default exists, show '(not set)'."""
        out = self._run(capsys, configured_max_tokens=None, default_max_tokens=None)
        assert "Max Output Tokens:  (not set)" in out

    def test_session_provider_wins_over_configured_default(self, capsys):
        """An explicit session provider (e.g. --provider deepseek) is reported."""
        out = self._run(capsys, provider="deepseek")
        assert "Provider:           deepseek" in out
        # The configured default ('openai') must not be shown instead.
        assert "Provider:           openai" not in out
