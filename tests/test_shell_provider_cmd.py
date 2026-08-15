"""
Tests for the shell /provider command handler.

``/provider`` switches the active provider for the shell session: it validates
the name against the supported providers (built-in ``PROVIDER_INFO`` entries
plus registered variants) and updates the shell's displayed provider/model
**without** changing the configured default ``provider`` in config.json
(that requires ``janito --set provider=<name>``).  ``/provider`` with no
argument lists the current provider and every available one.  The command
must not match non-``/provider`` input (e.g. ``/providers``) and must report
unknown providers without touching the config.

The switch takes effect in real time: the shell's send function is rebound to
the new provider (via ``send_factory``) and the LLM conversation history is
cleared (system prompt preserved), whether or not the session was started
with ``--provider``.  Switching to the same provider keeps both the history
and the send function.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_dir as config_dir_mod
from janito.config_store import get_config_value
from janito.provider_data import PROVIDER_INFO
from janito.shell import InteractiveShell
from janito.shell.cmds.provider import available_provider_names
from janito.shell.cmds.registry import get_registered_commands


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _shell(provider=None):
    """Build a fresh shell for testing (optionally CLI-bound to a provider)."""
    return InteractiveShell(model="test-model", no_history=True, provider=provider)


def _provider_handler():
    """Return the registered /provider command handler."""
    return next(c for c in get_registered_commands() if c.name == "/provider")


def test_provider_command_is_registered():
    """The /provider handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/provider" in names


def test_no_argument_lists_current_and_available(monkeypatch, tmp_path, capsys):
    """``/provider`` alone shows the current provider and every available one."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _provider_handler().handle(shell, "/provider") is True

    out = capsys.readouterr().out
    assert "Current provider: openai" in out
    for name in PROVIDER_INFO:
        assert name in out
    assert "Switch with: /provider <name>" in out


def test_no_argument_respects_session_provider(monkeypatch, tmp_path, capsys):
    """A session provider (--provider deepseek) is reported as current."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="deepseek")
    assert _provider_handler().handle(shell, "/provider") is True
    out = capsys.readouterr().out
    assert "Current provider: deepseek" in out


def test_switch_provider_updates_shell_without_changing_config(
    monkeypatch, tmp_path, capsys
):
    """``/provider deepseek`` updates the shell display but not the config default."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _provider_handler().handle(shell, "/provider deepseek") is True

    assert get_config_value("provider") is None
    assert shell.provider == "deepseek"
    assert "Provider switched to 'deepseek'" in capsys.readouterr().out


def test_switch_provider_is_case_insensitive(monkeypatch, tmp_path, capsys):
    """``/provider DEEPSEEK`` normalizes to the canonical provider casing."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _provider_handler().handle(shell, "/provider DEEPSEEK") is True

    assert get_config_value("provider") is None
    assert shell.provider == "deepseek"


def test_switch_to_registered_variant(monkeypatch, tmp_path, capsys):
    """A registered provider variant is accepted like a built-in provider."""
    import janito.config_variants as cv

    _use_temp_config(monkeypatch, tmp_path)
    cv.create_variant("alibaba-tokenplan")
    shell = _shell()
    assert _provider_handler().handle(shell, "/provider alibaba-tokenplan") is True

    assert get_config_value("provider") is None
    assert shell.provider == "alibaba-tokenplan"


def test_unknown_provider_is_rejected_without_changes(monkeypatch, tmp_path, capsys):
    """An unsupported name is reported and the config is left untouched."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="openai")
    assert _provider_handler().handle(shell, "/provider not-a-provider") is True

    out = capsys.readouterr().out
    assert "Error:" in out
    assert "Unknown provider 'not-a-provider'" in out
    assert get_config_value("provider") is None
    assert shell.provider == "openai"


def test_cli_bound_session_switch_applies_immediately(monkeypatch, tmp_path, capsys):
    """With --provider the switch still takes effect in real time: the session
    provider changes, the conversation is cleared and no 'stays in effect' note
    is printed, while the config default is left untouched."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="openai")
    assert _provider_handler().handle(shell, "/provider deepseek") is True

    out = capsys.readouterr().out
    assert "Provider switched to 'deepseek'" in out
    assert "started with --provider" not in out
    assert "Conversation history cleared (provider changed)." in out
    # History is reset to just the preserved system prompt.
    assert shell.messages_history == [{"role": "system", "content": "sys"}]
    assert get_config_value("provider") is None


def test_switch_updates_shell_model_display(monkeypatch, tmp_path, capsys):
    """The toolbar model is re-resolved for the new provider."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    shell.model = "old-model"
    assert _provider_handler().handle(shell, "/provider openai") is True

    assert shell.provider == "openai"
    assert shell.model == "gpt-5.6-luna"  # openai's built-in default model


def test_non_provider_input_is_not_handled(capsys):
    """``/providers`` (plural) must not match the /provider command."""
    shell = _shell()
    assert _provider_handler().handle(shell, "/providers") is False
    assert capsys.readouterr().out == ""


def test_available_provider_names_lists_builtin_and_variants(monkeypatch, tmp_path):
    """available_provider_names returns built-ins plus registered variants."""
    import janito.config_variants as cv

    _use_temp_config(monkeypatch, tmp_path)
    cv.create_variant("custom-local")

    names = list(available_provider_names())
    for name in PROVIDER_INFO:
        assert name in names
    assert "custom-local" in names


def test_available_provider_names_filters_by_prefix_case_insensitively():
    """available_provider_names matches the typed prefix case-insensitively."""
    names = list(available_provider_names("DEEP"))
    assert names == ["deepseek"]
    assert available_provider_names("zzz") == []


def test_available_provider_names_filters_by_api_key(monkeypatch, tmp_path):
    """With only_with_api_key=True, providers without an API key are excluded."""
    from janito.auth_config import set_api_key

    _use_temp_config(monkeypatch, tmp_path)
    set_api_key("deepseek", "sk-deepseek")  # pragma: allowlist secret

    names = list(available_provider_names(only_with_api_key=True))
    assert names == ["deepseek"]

    # The typed prefix is still applied on top of the key filter.
    assert list(available_provider_names("al", only_with_api_key=True)) == []
    assert list(available_provider_names("DEEP", only_with_api_key=True)) == [
        "deepseek"
    ]


def test_available_provider_names_default_ignores_api_key(monkeypatch, tmp_path):
    """The default (used by the /provider display) lists every provider."""
    from janito.auth_config import set_api_key

    _use_temp_config(monkeypatch, tmp_path)
    set_api_key("deepseek", "sk-deepseek")  # pragma: allowlist secret

    names = list(available_provider_names())
    for name in PROVIDER_INFO:
        assert name in names
    assert "deepseek" in names


# ---------------------------------------------------------------------------
# Conversation history clearing
# ---------------------------------------------------------------------------


def _shell_with_history(provider=None):
    """Build a shell with an initialized conversation containing one exchange."""
    shell = _shell(provider=provider)
    shell.initialize_history(system_prompt="sys")
    shell.messages_history.append({"role": "user", "content": "hello"})
    shell.messages_history.append({"role": "assistant", "content": "hi"})
    shell.previous_response_id = "resp-123"
    shell.conversation_items = [{"type": "message", "role": "user"}]
    return shell


def test_switch_provider_clears_conversation_history(monkeypatch, tmp_path, capsys):
    """Switching the effective provider clears the LLM conversation history."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history()

    assert _provider_handler().handle(shell, "/provider deepseek") is True

    out = capsys.readouterr().out
    assert "Conversation history cleared (provider changed)." in out
    # History is reset to just the preserved system prompt; the server-side
    # and client-side Responses conversation state is dropped too.
    assert shell.messages_history == [{"role": "system", "content": "sys"}]
    assert shell.previous_response_id is None
    assert shell.conversation_items is None


def test_switch_to_same_provider_keeps_history(monkeypatch, tmp_path, capsys):
    """Switching to the provider already in effect keeps the conversation."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history()

    assert _provider_handler().handle(shell, "/provider openai") is True

    out = capsys.readouterr().out
    assert "Conversation history cleared" not in out
    assert len(shell.messages_history) == 3
    assert shell.previous_response_id == "resp-123"


def test_cli_bound_session_switch_to_other_provider_clears_history(
    monkeypatch, tmp_path, capsys
):
    """In a --provider-bound session, a switch to another provider still
    rebinds the send function and clears the history immediately."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="openai")
    calls = []

    def factory(provider):
        calls.append(provider)
        return f"send:{provider}"

    shell.send_factory = factory
    shell.send_prompt_func = "send:openai"

    assert _provider_handler().handle(shell, "/provider deepseek") is True

    assert calls == ["deepseek"]
    assert shell.send_prompt_func == "send:deepseek"
    assert "Conversation history cleared (provider changed)." in capsys.readouterr().out
    # History is reset to just the preserved system prompt.
    assert shell.messages_history == [{"role": "system", "content": "sys"}]
    # The configured default is not changed for future sessions.
    assert get_config_value("provider") is None


def test_switch_to_same_provider_keeps_send_function(monkeypatch, tmp_path, capsys):
    """Switching to the provider already in effect keeps history and send function."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="openai")
    shell.send_factory = lambda provider: f"send:{provider}"
    shell.send_prompt_func = "send:openai"

    assert _provider_handler().handle(shell, "/provider openai") is True

    assert shell.send_prompt_func == "send:openai"
    assert "Conversation history cleared" not in capsys.readouterr().out
    assert len(shell.messages_history) == 3


def test_switch_from_one_provider_to_another_clears_history(
    monkeypatch, tmp_path, capsys
):
    """A second switch (openai -> deepseek -> alibaba) clears again."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history()

    assert _provider_handler().handle(shell, "/provider deepseek") is True
    capsys.readouterr().out  # drop first output

    shell.messages_history.append({"role": "user", "content": "next"})
    assert _provider_handler().handle(shell, "/provider alibaba") is True

    out = capsys.readouterr().out
    assert "Conversation history cleared (provider changed)." in out
    assert shell.messages_history == [{"role": "system", "content": "sys"}]
