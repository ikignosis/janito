"""
Tests for the --info handler output, in particular the ``Responses In Server``
line that reflects the resolved ``responses_in_server`` flag.

The line is shown only when the effective API type resolves to ``Responses``:
- server-side providers (e.g. OpenAI) report
  ``server-side (previous_response_id)``
- stateless providers (e.g. DeepSeek) report
  ``stateless (client re-sends history)``
- when the API type resolves to ``Completions`` the line is omitted.

Also covers ``--show-system-prompt`` (``handle_show_system_prompt``), in
particular that the "(with skills)" suffix is only shown when a ``skills``
section is actually present in the default prompt.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import janito.tooling.tools_registry as tools_registry_mod
from janito.cli.handlers.info import (
    handle_info,
    handle_show_config,
    handle_show_system_prompt,
)

SKILLS_SECTION = "## Available Skills\n(fake skills section)"


def _fake_resolve_api_type(cli_api_type, provider, model=None):
    """Deterministic stand-in for resolve_api_type.

    ``--api-type`` is honored; otherwise the API type defaults to Responses
    (matching OpenAI's built-in default).  ``model`` is accepted (ignored)
    for signature parity with the model-aware resolve_api_type.
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
    assert "API Type" in out
    assert "Responses" in out
    assert "Responses In Server" in out
    assert "server-side (previous_response_id)" in out


def test_responses_in_server_stateless_for_deepseek(capsys):
    """DeepSeek's /responses endpoint is stateless."""
    out = _run(capsys, provider="deepseek")
    assert "Responses" in out
    assert "stateless (client re-sends history)" in out


def test_responses_in_server_hidden_when_api_type_completions(capsys):
    """The line is omitted when the API type resolves to Completions."""
    out = _run(capsys, provider="openai", api_type="completions")
    assert "Completions" in out
    assert "Responses In Server" not in out


def test_responses_in_server_shown_when_api_type_forced_responses(capsys):
    """--api-type responses keeps the line even for a Completions-only provider."""
    out = _run(capsys, provider="minimax", api_type="responses")
    assert "Responses" in out
    assert "server-side (previous_response_id)" in out


def _run_show_config(
    capsys,
    provider="openai",
    cli_model=None,
    config_model=None,
    default_model=None,
):
    """Run handle_show_config with patched config lookups and capture output."""
    with (
        patch(
            "janito.cli.handlers.info.load_provider_from_config",
            return_value=provider,
        ),
        patch(
            "janito.cli.handlers.info.load_model_from_config",
            return_value=config_model,
        ),
        patch(
            "janito.cli.handlers.info.get_default_model_from_provider",
            return_value=default_model,
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
            "janito.cli.handlers.info.is_custom_provider",
            return_value=False,
        ),
        patch(
            "janito.cli.handlers.info.get_endpoint_for_api_type",
            return_value=None,
        ),
        patch(
            "janito.cli.handlers.info.get_default_thinking_from_provider",
            return_value=False,
        ),
    ):
        args = SimpleNamespace(provider=None, model=cli_model, api_type=None)
        handle_show_config(args)
    return capsys.readouterr().out


def test_show_config_uses_provider_default_model_when_unset(capsys):
    """No explicit model -> the provider's built-in default model is shown."""
    out = _run_show_config(
        capsys, provider="deepseek", default_model="deepseek-v4-flash"
    )
    assert "deepseek-v4-flash (deepseek default)" in out


def test_show_config_uses_configured_model(capsys):
    """A model set in config.json takes precedence over the provider default."""
    out = _run_show_config(
        capsys,
        provider="deepseek",
        config_model="my-model",
        default_model="deepseek-v4-flash",
    )
    assert "my-model (deepseek.model)" in out


def test_show_config_cli_model_overrides_config(capsys):
    """--model takes precedence over both config and the provider default."""
    out = _run_show_config(
        capsys,
        provider="deepseek",
        cli_model="gpt-x",
        config_model="my-model",
        default_model="deepseek-v4-flash",
    )
    assert "gpt-x (CLI argument)" in out


def test_show_config_no_default_model(capsys):
    """A provider without a default model still reports (not configured)."""
    out = _run_show_config(capsys, provider="custom", default_model=None)
    assert "(not configured)" in out


# --- --show-system-prompt -------------------------------------------------


def _run_show_system_prompt(capsys, monkeypatch, tmp_path, skills_section):
    """Run handle_show_system_prompt and return its captured output.

    ``skills_section`` is what ``get_skills_section`` should return; pass
    ``None`` to leave it unpatched (uses the real tool registry).
    """
    monkeypatch.chdir(tmp_path)
    if skills_section is not None:
        monkeypatch.setattr(
            tools_registry_mod, "get_skills_section", lambda: skills_section
        )
    args = SimpleNamespace(system_prompt=None, no_system_prompt=False)
    handle_show_system_prompt(args)
    return capsys.readouterr().out


def test_show_system_prompt_title_with_skills(capsys, monkeypatch, tmp_path):
    """A skills section present -> the title advertises (with skills)."""
    out = _run_show_system_prompt(capsys, monkeypatch, tmp_path, SKILLS_SECTION)
    assert "System prompt (default (with skills))" in out
    assert "skills" in out
    assert "(fake skills section)" in out


def test_show_system_prompt_title_without_skills(capsys, monkeypatch, tmp_path):
    """No skills section (no skills available) -> title omits (with skills)."""
    out = _run_show_system_prompt(capsys, monkeypatch, tmp_path, "")
    assert "System prompt (default)" in out
    assert "(with skills)" not in out


def test_show_system_prompt_no_skills_section_row(capsys, monkeypatch, tmp_path):
    """With no skills, no skills section row is rendered."""
    out = _run_show_system_prompt(capsys, monkeypatch, tmp_path, "")
    assert "skills" not in out


def test_show_system_prompt_override(capsys, monkeypatch, tmp_path):
    """A custom -S prompt is shown as-is, without the default title."""
    monkeypatch.chdir(tmp_path)
    args = SimpleNamespace(system_prompt="custom system prompt", no_system_prompt=False)
    handle_show_system_prompt(args)
    out = capsys.readouterr().out
    assert "custom system prompt" in out
    assert "(with skills)" not in out


def test_show_system_prompt_disabled(capsys, monkeypatch, tmp_path):
    """-Z / --no-system-prompt is reported as disabled."""
    monkeypatch.chdir(tmp_path)
    args = SimpleNamespace(system_prompt=None, no_system_prompt=True)
    handle_show_system_prompt(args)
    out = capsys.readouterr().out
    assert "disabled via -Z" in out
