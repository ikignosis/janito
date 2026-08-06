"""
Tests for the --info handler output, in particular the ``Responses In Server``
line that reflects the resolved ``responses_in_server`` flag.

The line is shown only when the effective API type resolves to ``Responses``:
- server-side providers (e.g. OpenAI) report
  ``server-side (previous_response_id)``
- stateless providers (e.g. DeepSeek) report
  ``stateless (client re-sends history)``
- when the API type resolves to ``Completions`` the line is omitted.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from janito.cli.handlers.info import handle_info


def _fake_resolve_api_type(cli_api_type, provider):
    """Deterministic stand-in for resolve_api_type.

    ``--api-type`` is honored; otherwise the API type defaults to Responses
    (matching OpenAI's built-in default).
    """
    if cli_api_type:
        normalized = str(cli_api_type).strip().capitalize()
        return "Responses" if normalized == "Responses" else "Completions"
    return "Responses"


def _run(capsys, provider="openai", api_type=None):
    """Run handle_info with patched config lookups and capture the output."""
    auth_path = MagicMock()
    auth_path.exists.return_value = False
    with (
        patch(
            "janito.cli.handlers.info.load_provider_from_config",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.get_default_provider",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.load_model_from_config",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.get_api_key",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.get_masked_api_key",
            return_value="(not set)",
        ),
        patch(
            "janito.cli.handlers.info.load_endpoint_from_config",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.resolve_api_type",
            side_effect=_fake_resolve_api_type,
        ),
        patch(
            "janito.cli.handlers.info.get_config_path",
            return_value="/tmp/config.json",
        ),
        patch(
            "janito.cli.handlers.info.get_auth_file_path",
            return_value=auth_path,
        ),
    ):
        args = SimpleNamespace(provider=provider, model=None, api_type=api_type)
        handle_info(args)
    return capsys.readouterr().out


def test_responses_in_server_shown_for_server_side_provider(capsys):
    """OpenAI defaults to Responses and keeps state server-side."""
    out = _run(capsys, provider="openai")
    assert "API Type:     Responses" in out
    assert "Responses In Server: server-side (previous_response_id)" in out


def test_responses_in_server_stateless_for_deepseek(capsys):
    """DeepSeek's /responses endpoint is stateless."""
    out = _run(capsys, provider="deepseek")
    assert "API Type:     Responses" in out
    assert "Responses In Server: stateless (client re-sends history)" in out


def test_responses_in_server_hidden_when_api_type_completions(capsys):
    """The line is omitted when the API type resolves to Completions."""
    out = _run(capsys, provider="openai", api_type="completions")
    assert "API Type:     Completions" in out
    assert "Responses In Server" not in out


def test_responses_in_server_shown_when_api_type_forced_responses(capsys):
    """--api-type responses keeps the line even for a Completions-only provider."""
    out = _run(capsys, provider="minimax", api_type="responses")
    assert "API Type:     Responses" in out
    assert "Responses In Server: server-side (previous_response_id)" in out
