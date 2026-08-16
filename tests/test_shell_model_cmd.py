"""
Tests for the shell /model command handler.

``/model`` switches the active model for the shell session: it updates the
shell's displayed model and rebinds the send function (via ``send_factory``
with a ``model_override``) so the new model takes effect in real time
**without** changing the configured default ``model`` in config.json (that
requires ``janito --set model=<name>``).  ``/model`` with no argument lists
the current model and the models available from the current provider.  The
command must not match non-``/model`` input (e.g. ``/models``).

Model names are open-ended (like the CLI's ``--model``): any name is accepted
and passed to the provider's API, but when it matches a model available from
the current provider (built-in registry + configured per-model entries) the
canonical casing is used.

Switching the model clears the LLM conversation history (system prompt
preserved); switching to the model already in effect keeps it.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from janito.config_store import get_config_value
from janito.shell import InteractiveShell
from janito.shell.cmds.model import available_model_names
from janito.shell.cmds.registry import get_registered_commands


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    import janito.config_dir as config_dir_mod

    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _shell(provider=None):
    """Build a fresh shell for testing (optionally CLI-bound to a provider)."""
    return InteractiveShell(model="test-model", no_history=True, provider=provider)


def _model_handler():
    """Return the registered /model command handler."""
    return next(c for c in get_registered_commands() if c.name == "/model")


def test_model_command_is_registered():
    """The /model handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/model" in names


def test_no_argument_lists_current_and_available(monkeypatch, tmp_path, capsys):
    """``/model`` alone shows the current model and the available ones."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="openai")
    assert _model_handler().handle(shell, "/model") is True

    out = capsys.readouterr().out
    assert "Current provider: openai" in out
    assert "Current model: test-model" in out
    assert "gpt-5.6-luna" in out  # openai's built-in model
    assert "Switch with: /model <name>" in out


def test_no_argument_marks_current_model(monkeypatch, tmp_path, capsys):
    """The current model is flagged in the available list."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="openai")
    shell.model = "gpt-5.6-luna"
    assert _model_handler().handle(shell, "/model") is True

    out = capsys.readouterr().out
    assert "gpt-5.6-luna (current)" in out


def test_switch_model_updates_shell_without_changing_config(
    monkeypatch, tmp_path, capsys
):
    """``/model deepseek-v4-flash`` updates the shell display but not the config."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="deepseek")
    assert _model_handler().handle(shell, "/model deepseek-v4-flash") is True

    assert get_config_value("deepseek.model") is None
    assert shell.model == "deepseek-v4-flash"
    assert shell.model_override == "deepseek-v4-flash"
    assert "Model switched to 'deepseek-v4-flash'" in capsys.readouterr().out


def test_switch_model_is_case_insensitive_and_canonicalizes(
    monkeypatch, tmp_path, capsys
):
    """``/model DEEPSEEK-V4-FLASH`` normalizes to the canonical model casing."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="deepseek")
    assert _model_handler().handle(shell, "/model DEEPSEEK-V4-FLASH") is True

    assert get_config_value("deepseek.model") is None
    assert shell.model == "deepseek-v4-flash"


def test_switch_model_accepts_open_ended_model_name(monkeypatch, tmp_path, capsys):
    """Like --model, an unknown-but-plausible name is accepted as typed."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell(provider="deepseek")
    # deepseek-v4-pro is served by DeepSeek but has no built-in registry entry.
    assert _model_handler().handle(shell, "/model deepseek-v4-pro") is True

    assert get_config_value("deepseek.model") is None
    assert shell.model == "deepseek-v4-pro"
    assert "Model switched to 'deepseek-v4-pro'" in capsys.readouterr().out


def test_non_model_input_is_not_handled(capsys):
    """``/models`` (plural) must not match the /model command."""
    shell = _shell()
    assert _model_handler().handle(shell, "/models") is False
    assert capsys.readouterr().out == ""


def test_available_model_names_lists_builtin_and_configured(monkeypatch, tmp_path):
    """available_model_names returns built-in models plus configured entries."""
    from janito.config_store import set_config_value

    _use_temp_config(monkeypatch, tmp_path)
    set_config_value("openai.models.gpt-future.max-output-tokens", 1000)

    names = list(available_model_names("openai"))
    assert "gpt-5.6-luna" in names
    assert "gpt-future" in names


def test_available_model_names_filters_by_prefix_case_insensitively():
    """available_model_names matches the typed prefix case-insensitively."""
    names = list(available_model_names("openai", "GPT"))
    assert names == ["gpt-5.6-luna"]
    assert available_model_names("openai", "zzz") == []


def test_available_model_names_unknown_provider_returns_empty():
    """An unknown provider has no available models."""
    assert available_model_names("not-a-provider") == []
    assert available_model_names(None) == []


# ---------------------------------------------------------------------------
# Conversation history clearing / send-function rebinding
# ---------------------------------------------------------------------------


def _shell_with_history(provider=None):
    """Build a shell with an initialized conversation containing one exchange."""
    shell = _shell(provider=provider)
    shell.initialize_history(system_prompt="sys")
    shell.messages_history.append({"role": "user", "content": "hello"})
    shell.messages_history.append({"role": "assistant", "content": "hi"})
    return shell


def test_switch_model_clears_conversation_history(monkeypatch, tmp_path, capsys):
    """Switching the model clears the LLM conversation history."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="deepseek")

    assert _model_handler().handle(shell, "/model deepseek-v4-pro") is True

    out = capsys.readouterr().out
    assert "Conversation history cleared (model changed)." in out
    # History is reset to just the preserved system prompt.
    assert shell.messages_history == [{"role": "system", "content": "sys"}]


def test_switch_to_same_model_keeps_history(monkeypatch, tmp_path, capsys):
    """Switching to the model already in effect keeps the conversation."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="deepseek")
    shell.model = "deepseek-v4-flash"

    assert _model_handler().handle(shell, "/model deepseek-v4-flash") is True

    out = capsys.readouterr().out
    assert "Conversation history cleared" not in out
    assert len(shell.messages_history) == 3


def test_switch_model_rebinds_send_function(monkeypatch, tmp_path, capsys):
    """The send function is rebuilt with the new model via send_factory."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="deepseek")
    calls = []

    def factory(provider, model_override=None):
        calls.append((provider, model_override))
        return f"send:{provider}:{model_override}"

    shell.send_factory = factory
    shell.send_prompt_func = "send:deepseek:None"

    assert _model_handler().handle(shell, "/model deepseek-v4-pro") is True

    assert calls == [("deepseek", "deepseek-v4-pro")]
    assert shell.send_prompt_func == "send:deepseek:deepseek-v4-pro"
    assert "Conversation history cleared (model changed)." in capsys.readouterr().out
    assert shell.messages_history == [{"role": "system", "content": "sys"}]


def test_provider_switch_clears_model_override(monkeypatch, tmp_path, capsys):
    """A /model override is scoped to its provider: /provider clears it."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell_with_history(provider="openai")
    shell.send_factory = lambda provider, model_override=None: f"send:{provider}"
    shell.send_prompt_func = "send:openai"

    # /model sets a session override on the current provider.
    assert _model_handler().handle(shell, "/model gpt-5.6-luna") is True
    assert shell.model_override == "gpt-5.6-luna"

    # /provider deepseek switches provider: the override is dropped and the
    # new provider's own model is resolved.
    provider_handler = next(
        c for c in get_registered_commands() if c.name == "/provider"
    )
    assert provider_handler.handle(shell, "/provider deepseek") is True

    assert shell.model_override is None
    assert shell.provider == "deepseek"
    assert shell.model == "deepseek-v4-flash"  # deepseek's built-in default
