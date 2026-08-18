"""
Tests for the shell /thinking command handler.

``/thinking on|off`` enables or disables runtime config thinking for the
running shell session without altering the persisted configuration in config.json.
``/thinking`` alone reports the current thinking status and usage.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from janito.shell import InteractiveShell
from janito.shell.cmds.registry import get_registered_commands
from janito.shell.session import _thinking_arg_completer


def _shell(thinking: bool = False, provider: str | None = None) -> InteractiveShell:
    """Build a fresh shell for testing."""
    return InteractiveShell(
        model="test-model",
        no_history=True,
        provider=provider,
        thinking=thinking,
    )


def _thinking_handler():
    """Return the registered /thinking command handler."""
    return next(c for c in get_registered_commands() if c.name == "/thinking")


def test_thinking_command_is_registered():
    """The /thinking handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/thinking" in names


def test_no_argument_shows_disabled_status_by_default(capsys):
    """``/thinking`` alone shows disabled status when thinking is off."""
    shell = _shell(thinking=False)
    assert _thinking_handler().handle(shell, "/thinking") is True

    out = capsys.readouterr().out
    assert "Thinking mode is currently disabled (off) for this session." in out
    assert "Usage: /thinking on|off" in out


def test_no_argument_shows_enabled_status_when_on(capsys):
    """``/thinking`` alone shows enabled status when thinking is on."""
    shell = _shell(thinking=True)
    assert _thinking_handler().handle(shell, "/thinking") is True

    out = capsys.readouterr().out
    assert "Thinking mode is currently enabled (on) for this session." in out
    assert "Usage: /thinking on|off" in out


def test_thinking_on_enables_thinking(capsys):
    """``/thinking on`` sets shell.thinking to True."""
    shell = _shell(thinking=False)
    assert _thinking_handler().handle(shell, "/thinking on") is True

    assert shell.thinking is True
    out = capsys.readouterr().out
    assert "[OK] Thinking mode enabled for this session" in out
    assert "(config default unchanged)" in out


def test_thinking_off_disables_thinking(capsys):
    """``/thinking off`` sets shell.thinking to False."""
    shell = _shell(thinking=True)
    assert _thinking_handler().handle(shell, "/thinking off") is True

    assert shell.thinking is False
    out = capsys.readouterr().out
    assert "[OK] Thinking mode disabled for this session" in out
    assert "(config default unchanged)" in out


def test_thinking_case_insensitive(capsys):
    """Arguments 'ON' and 'OFF' are recognized case-insensitively."""
    shell = _shell(thinking=False)
    assert _thinking_handler().handle(shell, "/THINKING ON") is True
    assert shell.thinking is True

    assert _thinking_handler().handle(shell, "/Thinking Off") is True
    assert shell.thinking is False


def test_thinking_invalid_argument_prints_error(capsys):
    """An invalid argument reports an error and leaves thinking unchanged."""
    shell = _shell(thinking=False)
    assert _thinking_handler().handle(shell, "/thinking invalid") is True

    assert shell.thinking is False
    out = capsys.readouterr().out
    assert (
        "Error: Invalid option 'invalid'. Use '/thinking on' or '/thinking off'." in out
    )


def test_non_thinking_command_is_not_handled(capsys):
    """Commands that do not match /thinking return False."""
    shell = _shell()
    assert _thinking_handler().handle(shell, "/think") is False
    assert _thinking_handler().handle(shell, "/thinkingmode") is False
    assert _thinking_handler().handle(shell, "thinking on") is False
    assert capsys.readouterr().out == ""


def test_thinking_arg_completer():
    """_thinking_arg_completer returns matching options."""
    assert _thinking_arg_completer("") == ["on", "off"]
    assert _thinking_arg_completer("o") == ["on", "off"]
    assert _thinking_arg_completer("on") == ["on"]
    assert _thinking_arg_completer("of") == ["off"]
    assert _thinking_arg_completer("off") == ["off"]
    assert _thinking_arg_completer("ON") == ["on"]
    assert _thinking_arg_completer("z") == []


def test_thinking_argument_autocompletion_in_shell_session():
    """Autocompletion works on shell session for /thinking."""
    shell = _shell()
    doc = Document("/thinking o", cursor_position=len("/thinking o"))
    completions = list(shell.session.completer.get_completions(doc, CompleteEvent()))
    completion_texts = [c.text for c in completions]
    assert "on" in completion_texts
    assert "off" in completion_texts


def test_status_command_reflects_thinking_toggle(capsys):
    """/status command displays updated thinking mode after /thinking on/off."""
    from janito.shell.cmds.status import StatusCmdHandler

    status_handler = StatusCmdHandler()
    shell = _shell(thinking=False, provider="openai")

    # Status before toggle
    assert status_handler.handle(shell, "/status") is True
    out1 = capsys.readouterr().out
    assert "disabled" in out1

    # Toggle on
    assert _thinking_handler().handle(shell, "/thinking on") is True
    capsys.readouterr()

    # Status after toggle on
    assert status_handler.handle(shell, "/status") is True
    out2 = capsys.readouterr().out
    assert "enabled" in out2
