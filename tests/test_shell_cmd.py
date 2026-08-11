"""
Tests for the ``!cmd`` shell command execution.

The interactive shell runs ``!<command>`` input through
:meth:`janito.shell.interactive.InteractiveShell._run_shell_command`. These
tests verify that the command is executed with the real terminal inherited
(so interactive, full-screen programs such as vim work), that the exit code
is reported, that errors and Ctrl+C are handled gracefully, that the parent
SIGINT handler is restored, and that the cooked-terminal context manager
forces cooked mode and restores the terminal state even on errors.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.shell import InteractiveShell


def _shell():
    """Build a fresh shell for testing."""
    return InteractiveShell(model="test-model", no_history=True)


def test_shell_cmd_runs_and_prints_output(capfd):
    """A ``!cmd`` runs with the terminal inherited and reports the exit code."""
    shell = _shell()
    shell._run_shell_command("!echo hello-from-shell")
    out = capfd.readouterr().out
    assert "[Shell] Executing: echo hello-from-shell" in out
    assert "hello-from-shell" in out
    assert "[Shell] Exit code: 0" in out


def test_shell_cmd_reports_nonzero_exit_code(capfd):
    """The exit code of the command is reported to the user."""
    shell = _shell()
    shell._run_shell_command("!exit 3")
    out = capfd.readouterr().out
    assert "[Shell] Exit code: 3" in out


def test_shell_cmd_empty_is_noop(capfd):
    """A bare ``!`` (no command) does nothing."""
    shell = _shell()
    shell._run_shell_command("!")
    assert capfd.readouterr().out == ""
    shell._run_shell_command("!   ")
    assert capfd.readouterr().out == ""


def test_shell_cmd_error_is_reported(monkeypatch, capfd):
    """Unexpected subprocess failures are reported without crashing."""
    shell = _shell()

    def boom(cmd, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("janito.shell.interactive.subprocess.run", boom)
    shell._run_shell_command("!anything")
    err = capfd.readouterr().err
    assert "[Shell] Error: boom" in err


def test_shell_cmd_keyboard_interrupt_is_handled(monkeypatch, capfd):
    """A KeyboardInterrupt during the command is reported and swallowed."""
    shell = _shell()

    def interrupted(cmd, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("janito.shell.interactive.subprocess.run", interrupted)
    shell._run_shell_command("!anything")
    err = capfd.readouterr().err
    assert "[Shell] Command interrupted" in err


def test_shell_cmd_ignores_sigint_while_running_and_restores_it(monkeypatch, capfd):
    """SIGINT is ignored in the parent while the command runs, then restored."""
    shell = _shell()
    seen = {}

    def record(cmd, **kwargs):
        seen["handler"] = signal.getsignal(signal.SIGINT)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("janito.shell.interactive.subprocess.run", record)
    old = signal.getsignal(signal.SIGINT)
    shell._run_shell_command("!echo ok")
    assert seen["handler"] == signal.SIG_IGN
    assert signal.getsignal(signal.SIGINT) == old


def test_shell_cmd_dispatched_from_run_loop(monkeypatch, capfd):
    """Typing ``!<cmd>`` at the prompt executes the command in the shell."""
    shell = _shell()
    shell.initialize_history(system_prompt="sys")
    calls = {"n": 0}

    def fake_prompt(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "!echo dispatched-ok"
        raise EOFError

    monkeypatch.setattr(shell.session, "prompt", fake_prompt)
    shell.run(send_prompt_func=lambda *a, **k: None, no_tools=True)
    out = capfd.readouterr().out
    assert "dispatched-ok" in out
    assert "[Shell] Exit code: 0" in out


@pytest.mark.skipif(os.name == "nt", reason="termios is POSIX-only")
def test_cooked_terminal_forces_cooked_mode_and_restores(monkeypatch):
    """_cooked_terminal forces cooked mode and restores the state on errors."""
    import termios

    shell = _shell()

    class _FakeStdin:
        def __init__(self, fd):
            self._fd = fd

        def isatty(self):
            return True

        def fileno(self):
            return self._fd

    master, slave = os.openpty()
    try:
        fd = os.dup(slave)
        fake = _FakeStdin(fd)
        monkeypatch.setattr(sys, "stdin", fake)

        original = termios.tcgetattr(fd)
        with shell._cooked_terminal():
            inside = termios.tcgetattr(fd)
            assert inside[3] & termios.ICANON
            assert inside[3] & termios.ECHO
        assert termios.tcgetattr(fd) == original

        # The state is restored even when the wrapped command raises.
        with pytest.raises(RuntimeError):
            with shell._cooked_terminal():
                raise RuntimeError("kaboom")
        assert termios.tcgetattr(fd) == original
    finally:
        os.close(slave)
        os.close(master)
