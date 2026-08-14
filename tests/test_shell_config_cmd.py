"""Tests for the shell /status command handler."""

from unittest.mock import patch

from janito.shell.cmds.status import _print_config_info


class TestPrintConfigInfo:
    """Tests for _print_config_info display logic (tokens, thinking, API type)."""

    def _run(
        self,
        capsys,
        provider=None,
        configured_max_tokens=None,
        default_max_tokens=128000,
        thinking=False,
        api_type="Responses",
        responses_in_server=True,
    ):
        """Helper: patch config lookups and capture printed output.

        Args:
            provider: The session provider to pass to ``_print_config_info``.
                When None, the (patched) configured default is used.
            thinking: The ``--thinking`` CLI flag passed to ``_print_config_info``.
            api_type: The effective API type returned by ``resolve_api_type``.
            responses_in_server: Value returned by
                ``get_responses_in_server_from_provider`` (only meaningful when
                ``api_type`` is ``Responses``).
        """
        with (
            patch(
                "janito.shell.cmds.status.get_active_provider",
                return_value="openai",
            ),
            patch(
                "janito.shell.cmds.status.get_api_key",
                return_value="sk-test-key-1234567890",
            ),
            patch(
                "janito.shell.cmds.status.get_masked_api_key",
                return_value="sk-***7890",
            ),
            patch(
                "janito.shell.cmds.status.load_max_output_tokens",
                return_value=configured_max_tokens,
            ),
            patch(
                "janito.shell.cmds.status.load_endpoint_from_config",
                return_value=None,
            ),
            patch(
                "janito.shell.cmds.status.get_default_max_output_tokens_from_provider",
                return_value=default_max_tokens,
            ),
            patch(
                "janito.shell.cmds.status.resolve_api_type",
                return_value=api_type,
            ),
            patch(
                "janito.shell.cmds.status.get_responses_in_server_from_provider",
                return_value=responses_in_server,
            ),
        ):
            _print_config_info(provider, thinking)
        return capsys.readouterr().out

    def test_explicit_max_output_tokens_shown_as_is(self, capsys):
        """When the user has set max output tokens, display them without suffix."""
        out = self._run(capsys, configured_max_tokens=65536)
        assert "Max Output Tokens" in out
        assert "65536" in out
        assert "(default)" not in out

    def test_falls_back_to_provider_default(self, capsys):
        """When not configured, the provider's built-in default is shown with '(default)'."""
        out = self._run(capsys, configured_max_tokens=None, default_max_tokens=128000)
        assert "128000 (default)" in out

    def test_not_set_when_no_default_available(self, capsys):
        """When neither configured nor a provider default exists, show '(not set)'."""
        out = self._run(capsys, configured_max_tokens=None, default_max_tokens=None)
        assert "Max Output Tokens" in out
        assert "(not set)" in out

    def test_session_provider_wins_over_configured_default(self, capsys):
        """An explicit session provider (e.g. --provider deepseek) is reported."""
        out = self._run(capsys, provider="deepseek")
        assert "deepseek" in out
        # The configured default ('openai') must not be shown instead.
        assert "openai" not in out

    def test_thinking_enabled_by_provider_default(self, capsys):
        """DeepSeek reasons by default: thinking shows 'enabled (model default)'."""
        out = self._run(capsys, provider="deepseek")
        assert "enabled (model default)" in out

    def test_thinking_disabled_by_default(self, capsys):
        """OpenAI has no default thinking: thinking shows 'disabled'."""
        out = self._run(capsys, provider="openai")
        assert "disabled" in out

    def test_thinking_flag_overrides_provider_default(self, capsys):
        """The --thinking flag forces thinking on without the '(model default)' note."""
        out = self._run(capsys, provider="openai", thinking=True)
        assert "enabled" in out
        assert "(model default)" not in out

    def test_responses_in_server_shown_for_server_side_provider(self, capsys):
        """Responses API + server-side state reports previous_response_id chaining."""
        out = self._run(capsys, api_type="Responses", responses_in_server=True)
        assert "API Type" in out
        assert "Responses" in out
        assert "Responses In Server" in out
        assert "server-side (previous_response_id)" in out

    def test_responses_in_server_stateless_for_deepseek(self, capsys):
        """DeepSeek's /responses endpoint is stateless."""
        out = self._run(
            capsys, provider="deepseek", api_type="Responses", responses_in_server=False
        )
        assert "Responses" in out
        assert "stateless (client re-sends history)" in out

    def test_responses_in_server_hidden_when_api_type_completions(self, capsys):
        """The line is omitted when the API type resolves to Completions."""
        out = self._run(capsys, provider="openai", api_type="Completions")
        assert "Completions" in out
        assert "Responses In Server" not in out
