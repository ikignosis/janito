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
from janito.openai_client.completions_api import (
    _is_enter_pressed,
    _run_with_progress_bar,
)
from janito.shell import InteractiveShell

# ---------------------------------------------------------------------------
# Non-blocking Enter detection
# ---------------------------------------------------------------------------


def test_is_enter_pressed_false_when_stdin_not_tty(monkeypatch):
    """Piped/redirected stdin must never be consumed by the Enter check."""

    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr("janito.openai_client.completions_api.sys.stdin", FakeStdin())
    assert _is_enter_pressed() is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only pty test")
def test_is_enter_pressed_posix_detects_enter(monkeypatch):
    """On POSIX a full line (an Enter press) is reported readable at once."""
    import os
    import pty

    master_fd, slave_fd = pty.openpty()
    try:
        stdin = os.fdopen(slave_fd, "r", buffering=1)
        monkeypatch.setattr("janito.openai_client.completions_api.sys.stdin", stdin)
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
        "janito.openai_client.completions_api._is_enter_pressed",
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


def _run_shell_turn(monkeypatch, send_prompt_func, shell=None):
    """Run one shell turn with a fake prompt (second prompt raises EOFError).

    Args:
        shell: Optional pre-configured shell to drive; a fresh one is created
            when not given (with history initialized to a "sys" prompt).
    """
    if shell is None:
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


def test_shell_enter_cancel_next_turn_keeps_context(monkeypatch):
    """After an Enter-cancel the next prompt is sent with the full history,
    including the cancelled message (the LLM must not lose the context)."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")

    sent_context = []
    calls = {"n": 0}

    def fake_prompt(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "hello"
        if calls["n"] == 2:
            return "continue"
        raise EOFError  # end the session on the third prompt

    def send_prompt_func(user_input, **kwargs):
        messages = kwargs["previous_messages"]
        # Snapshot what the LLM would see for this turn (before appending).
        sent_context.append([m.get("content") for m in messages])
        messages.append({"role": "user", "content": user_input})
        if calls["n"] == 1:
            # First turn is interrupted by Enter.
            raise RequestCancelled("cancelled by Enter")
        # Second turn completes normally.
        messages.append({"role": "assistant", "content": "ok"})
        return "ok"

    monkeypatch.setattr(shell.session, "prompt", fake_prompt)
    shell.run(send_prompt_func, no_tools=True)

    # The second (successful) turn saw the cancelled "hello" message too.
    assert len(sent_context) == 2
    assert "hello" in sent_context[1]


def test_shell_enter_cancel_server_side_keeps_completed_id_and_pending_items(
    monkeypatch,
):
    """Server-side Responses: Enter-cancel must NOT chain the next turn from
    the aborted response id -- the provider discards interrupted streams, so
    chaining from it fails with ``previous_response_id not found`` (the
    reported bug). The shell keeps the last completed response id and stores
    the cancelled message as pending items so the next turn re-sends them
    chained from the completed response."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.previous_response_id = "r1"

    def send_prompt_func(user_input, **kwargs):
        # Mirrors conversations_api._run_stream_round: the client hands back
        # the pending user messages (never the aborted response id).
        exc = RequestCancelled("cancelled by Enter")
        exc.conversation_items = [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_input}],
            }
        ]
        raise exc

    _run_shell_turn(monkeypatch, send_prompt_func, shell=shell)

    # The next turn keeps chaining from the last completed response...
    assert shell.previous_response_id == "r1"
    # ...and re-sends the cancelled message as input items.
    assert shell.conversation_items == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        }
    ]


def test_shell_enter_cancel_server_side_tool_round_keeps_completed_id(monkeypatch):
    """Server-side Responses: an Enter-cancel during a tool-call round (the
    user's message is already inside a completed response, so there are no
    pending items to re-send) leaves the conversation state untouched -- the
    shell keeps chaining from the last completed response id."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.previous_response_id = "r1"

    def send_prompt_func(user_input, **kwargs):
        exc = RequestCancelled("cancelled by Enter")
        exc.conversation_items = None  # tool round: nothing to re-send
        raise exc

    _run_shell_turn(monkeypatch, send_prompt_func, shell=shell)

    assert shell.previous_response_id == "r1"
    assert shell.conversation_items is None


def test_shell_enter_cancel_server_side_next_turn_resends_cancelled_message(
    monkeypatch,
):
    """After an Enter-cancel on a server-side conversation, the next turn is
    sent with previous_response_id pointing at the last *completed* response
    and previous_items carrying the cancelled message, so the LLM keeps the
    context without hitting previous_response_not_found (the reported bug)."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.previous_response_id = "r1"

    sent = []
    calls = {"n": 0}

    def fake_prompt(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "which files did you read?"
        if calls["n"] == 2:
            return "thanks"
        raise EOFError  # end the session on the third prompt

    def send_prompt_func(user_input, **kwargs):
        sent.append(
            {
                "previous_response_id": kwargs["previous_response_id"],
                "previous_items": list(kwargs["previous_items"] or []),
            }
        )
        if calls["n"] == 1:
            # First turn is interrupted by Enter: the client hands back the
            # cancelled message as pending items (no aborted response id).
            exc = RequestCancelled("cancelled by Enter")
            exc.conversation_items = [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_input}],
                }
            ]
            raise exc
        return "ok"

    monkeypatch.setattr(shell.session, "prompt", fake_prompt)
    shell.run(send_prompt_func, no_tools=True)

    # The cancelled turn chained from the last completed response.
    assert sent[0]["previous_response_id"] == "r1"
    # The next turn still chains from the completed response (never from an
    # aborted id) and re-sends the cancelled message as input items.
    assert sent[1]["previous_response_id"] == "r1"
    user_texts = [
        item["content"][0]["text"]
        for item in sent[1]["previous_items"]
        if item.get("role") == "user"
    ]
    assert user_texts == ["which files did you read?"]


def test_shell_enter_cancel_stateless_keeps_cancelled_message(monkeypatch):
    """Stateless Responses (e.g. DeepSeek): Enter-cancel persists the cancelled
    message into the client-side items so the next turn re-sends it."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.conversation_items = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "first"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "reply"}],
        },
    ]

    def send_prompt_func(user_input, **kwargs):
        raise RequestCancelled("cancelled by Enter")

    _run_shell_turn(monkeypatch, send_prompt_func, shell=shell)

    user_texts = [
        item["content"][0]["text"]
        for item in shell.conversation_items
        if item.get("role") == "user"
    ]
    # The cancelled message was persisted alongside the previous ones.
    assert user_texts == ["first", "hello"]


def test_shell_enter_cancel_stateless_fresh_conversation_keeps_context(monkeypatch):
    """Stateless Responses (e.g. DeepSeek) on a FRESH conversation: the first
    message is cancelled with Enter. The client hands back the full client-side
    items (system + cancelled message) on the exception, so the shell keeps
    them even though it had no items yet (regression: the next turn used to
    start a brand-new conversation and the LLM lost all context)."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    assert shell.conversation_items is None  # fresh conversation

    def send_prompt_func(user_input, **kwargs):
        # Mirrors conversations_api._run_stream_round for stateless mode: the
        # exception carries the full items including the cancelled message.
        exc = RequestCancelled("cancelled by Enter")
        exc.conversation_items = [
            {
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": "sys"}],
            },
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hello"}],
            },
        ]
        raise exc

    _run_shell_turn(monkeypatch, send_prompt_func, shell=shell)

    user_texts = [
        item["content"][0]["text"]
        for item in shell.conversation_items
        if item.get("role") == "user"
    ]
    # The cancelled first message is kept for the next turn.
    assert user_texts == ["hello"]
    assert shell.previous_response_id is None  # stateless: never chains


def test_shell_enter_cancel_stateless_next_turn_sends_full_items(monkeypatch):
    """After an Enter-cancel on a stateless conversation, the next successful
    turn re-sends the full items including the cancelled message, so the LLM
    keeps the previous messages (the reported regression: DeepSeek answered
    "I have no prior context" after an Enter-cancel)."""
    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")

    sent_items = []
    calls = {"n": 0}

    def fake_prompt(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "read these files"
        if calls["n"] == 2:
            return "which files did you read?"
        raise EOFError  # end the session on the third prompt

    def send_prompt_func(user_input, **kwargs):
        if calls["n"] == 1:
            # First turn is interrupted by Enter; the stateless client hands
            # back the full items (system + the cancelled message).
            exc = RequestCancelled("cancelled by Enter")
            exc.conversation_items = [
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "sys"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "read these files"}],
                },
            ]
            raise exc
        # Second turn completes normally: snapshot what the LLM receives.
        sent_items.append(list(kwargs["previous_items"] or []))
        return "ok"

    monkeypatch.setattr(shell.session, "prompt", fake_prompt)
    shell.run(send_prompt_func, no_tools=True)

    assert len(sent_items) == 1
    user_texts = [
        item["content"][0]["text"]
        for item in sent_items[0]
        if item.get("role") == "user"
    ]
    # The second turn saw the cancelled message, so the LLM has the context.
    assert user_texts == ["read these files"]


def test_run_with_progress_bar_attaches_partial_result(monkeypatch):
    """The cancelled request's partial result (e.g. the aborted response id)
    is carried on the RequestCancelled exception for the caller."""
    started = threading.Event()

    def slow_worker(cancel_event=None):
        started.set()
        while not cancel_event.is_set():
            time.sleep(0.01)
        return ("partial", None, [], None, "resp_aborted")

    monkeypatch.setattr(
        "janito.openai_client.completions_api._is_enter_pressed",
        lambda: started.is_set(),
    )

    with pytest.raises(RequestCancelled) as excinfo:
        _run_with_progress_bar(slow_worker)
    # The worker honoured the cancel and returned its partial result.
    assert excinfo.value.partial_result == ("partial", None, [], None, "resp_aborted")
