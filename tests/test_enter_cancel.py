"""
Tests for the Enter-to-cancel behaviour while "Waiting for response from the
API server...".

Pressing Enter while a request is pending aborts the in-flight stream and
raises :class:`RequestCancelled` -- an *interrupt without rollback*: unlike
Ctrl+C (``KeyboardInterrupt``), the user's message stays in the conversation
history so the chat can continue from where it was interrupted.
"""

import sys
import threading
import time

import pytest

from janito.openai_client import RequestCancelled
from janito.openai_client.client import _is_enter_pressed, _run_with_progress_bar
from janito.shell import InteractiveShell

# ---------------------------------------------------------------------------
# Non-blocking Enter detection
# ---------------------------------------------------------------------------


def test_is_enter_pressed_false_when_stdin_not_tty(monkeypatch):
    """Piped/redirected stdin must never be consumed by the Enter check."""

    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr("janito.openai_client.client.sys.stdin", FakeStdin())
    assert _is_enter_pressed() is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only pty test")
def test_is_enter_pressed_posix_detects_enter(monkeypatch):
    """On POSIX a full line (an Enter press) is reported readable at once."""
    import os
    import pty

    master_fd, slave_fd = pty.openpty()
    try:
        stdin = os.fdopen(slave_fd, "r", buffering=1)
        monkeypatch.setattr("janito.openai_client.client.sys.stdin", stdin)
        os.write(master_fd, b"hello\n")
        assert _is_enter_pressed() is True
        # The line was consumed; there is nothing left to read.
        assert _is_enter_pressed() is False
    finally:
        os.close(master_fd)


# ---------------------------------------------------------------------------
# _run_with_progress_bar cancel semantics
# ---------------------------------------------------------------------------


def test_run_with_progress_bar_raises_request_cancelled_on_enter(monkeypatch):
    """Pressing Enter while the worker runs aborts it and raises RequestCancelled."""
    started = threading.Event()

    def slow_worker(cancel_event=None):
        started.set()
        while not cancel_event.is_set():
            time.sleep(0.01)
        return "partial"

    # Simulate the user pressing Enter as soon as the worker has started.
    monkeypatch.setattr(
        "janito.openai_client.client._is_enter_pressed",
        lambda: started.is_set(),
    )

    with pytest.raises(RequestCancelled):
        _run_with_progress_bar(slow_worker)


def test_run_with_progress_bar_returns_result_when_no_cancel():
    """Without an Enter press the worker's result is returned unchanged."""

    def worker(cancel_event=None):
        return "done"

    assert _run_with_progress_bar(worker) == "done"


def test_run_with_progress_bar_propagates_worker_exception():
    """A real worker exception still propagates (not masked as a cancel)."""

    def worker(cancel_event=None):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        _run_with_progress_bar(worker)


# ---------------------------------------------------------------------------
# Shell history semantics: Enter = interrupt without rollback, Ctrl+C = rollback
# ---------------------------------------------------------------------------


def _run_shell_turn(monkeypatch, send_prompt_func):
    """Run one shell turn with a fake prompt (second prompt raises EOFError)."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")

    calls = {"n": 0}

    def fake_prompt(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "hello"
        raise EOFError  # end the session on the next prompt

    monkeypatch.setattr(shell.session, "prompt", fake_prompt)
    shell.run(send_prompt_func, no_tools=True)
    return shell


def _appending_send_prompt_factory(raised_exc):
    """Mirror real send_prompt: append the user message, then raise."""

    def send_prompt_func(user_input, **kwargs):
        kwargs["previous_messages"].append({"role": "user", "content": user_input})
        raise raised_exc

    return send_prompt_func


def test_shell_enter_cancel_preserves_history(monkeypatch, capsys):
    """Enter-cancel keeps the user's message in the conversation history."""
    shell = _run_shell_turn(
        monkeypatch,
        _appending_send_prompt_factory(RequestCancelled("cancelled by Enter")),
    )

    assert any(
        m.get("role") == "user" and m.get("content") == "hello"
        for m in shell.messages_history
    )
    out = capsys.readouterr().out
    assert "cancelled" in out.lower()


def test_shell_ctrl_c_still_rolls_back(monkeypatch, capsys):
    """Ctrl+C keeps rolling the conversation history back (regression)."""
    shell = _run_shell_turn(
        monkeypatch, _appending_send_prompt_factory(KeyboardInterrupt())
    )

    assert not any(m.get("role") == "user" for m in shell.messages_history)
    out = capsys.readouterr().out
    assert "removed from the conversation history" in out
