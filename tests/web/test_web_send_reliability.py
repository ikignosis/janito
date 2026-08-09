"""Contract tests for reliable message submission in the web chat.

The web input box used to silently swallow submissions in several
situations: pressing Enter while a response was in flight (waiting /
streaming / tool_running) returned early and left the typed text in the
box with no feedback, and a submission made while the active session was
missing (page still bootstrapping, or the conversation just deleted) was
dropped the same way. A failed socket send also cleared the input *before*
the message was handed to the server, losing the typed text.

These tests pin down:

1. ``sendPrompt`` blocks a busy submission with a toast (keeps the text)
   instead of silently returning;
2. ``sendPrompt`` blocks a submission with no active session with a toast
   instead of silently returning;
3. the socket send is attempted BEFORE the input is cleared / the user
   message is pushed, so a failed send keeps the typed text;
4. the Send button is disabled for every non-idle status (including
   ``tool_running``, which previously left it enabled while the server
   silently discarded mid-turn prompts);
5. ``_await_cancel`` (backend) queues prompts that arrive mid-turn instead
   of discarding them, so the main loop can process them afterwards.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from _frontend import render_index_html

# The web routes need the optional `web` extra (fastapi). Skip gracefully
# when fastapi is not installed (e.g. minimal tox envs).
try:
    import fastapi  # noqa: F401
    from fastapi import WebSocketDisconnect

    _HAS_FASTAPI = True
except ModuleNotFoundError:
    _HAS_FASTAPI = False

requires_fastapi = pytest.mark.skipif(
    not _HAS_FASTAPI, reason="fastapi (web extra) is not installed"
)

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


# ---------------------------------------------------------------------------
# Backend: mid-turn prompts are queued, not discarded
# ---------------------------------------------------------------------------


class _FakeWebSocket:
    """Minimal stand-in with a canned receive_text() feed."""

    def __init__(self, frames):
        self._frames = list(frames)

    async def receive_text(self):
        if not self._frames:
            raise WebSocketDisconnect()
        return self._frames.pop(0)


@requires_fastapi
def test_await_cancel_queues_mid_turn_prompts():
    """Prompts arriving during a turn are queued, then cancel returns True."""
    from janito.web.backend.routers.chat import _await_cancel

    ws = _FakeWebSocket(
        [
            json.dumps({"type": "prompt", "content": "first"}),
            json.dumps({"type": "prompt", "content": "  second  "}),
            json.dumps({"type": "cancel"}),
        ]
    )
    pending: list[str] = []
    result = asyncio.run(_await_cancel(ws, pending))

    assert result is True
    # Both prompts were preserved (whitespace-trimmed) for the main loop.
    assert pending == ["first", "second"]


@requires_fastapi
def test_await_cancel_skips_empty_prompts():
    """Blank prompts are not queued (they would be rejected anyway)."""
    from janito.web.backend.routers.chat import _await_cancel

    ws = _FakeWebSocket(
        [
            json.dumps({"type": "prompt", "content": "   "}),
            json.dumps({"type": "prompt", "content": "ok"}),
            json.dumps({"type": "cancel"}),
        ]
    )
    pending: list[str] = []
    result = asyncio.run(_await_cancel(ws, pending))

    assert result is True
    assert pending == ["ok"]


@requires_fastapi
def test_await_cancel_returns_false_on_disconnect():
    """A disconnect (no cancel) reports False so the caller stops."""
    from janito.web.backend.routers.chat import _await_cancel

    ws = _FakeWebSocket([])
    result = asyncio.run(_await_cancel(ws, []))
    assert result is False


@requires_fastapi
def test_await_cancel_ignores_unknown_message_types():
    """Pings/unknown frames are ignored without losing queued prompts."""
    from janito.web.backend.routers.chat import _await_cancel

    ws = _FakeWebSocket(
        [
            json.dumps({"type": "ping"}),
            json.dumps({"type": "prompt", "content": "hello"}),
            json.dumps({"type": "cancel"}),
        ]
    )
    pending: list[str] = []
    result = asyncio.run(_await_cancel(ws, pending))

    assert result is True
    assert pending == ["hello"]


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def test_send_prompt_blocks_busy_submission_with_feedback():
    """A submission while a request is in flight shows a toast, keeps text."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    # The busy guard now covers every non-idle status (waiting, streaming,
    # tool_running) and reports it instead of silently returning.
    assert "if (this.status !== 'idle')" in js
    assert "_notifySendBlocked(" in js
    # The toast is dispatched through the root app component.
    assert "janito-toast" in js


def test_send_prompt_blocks_without_active_session():
    """No active session -> toast telling the user, not a silent no-op."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    assert "const id = this.sessionId;" in js
    assert "if (!id) {" in js
    assert "No active conversation" in js


def test_socket_send_happens_before_input_is_cleared():
    """The socket handoff precedes clearing the input / pushing the message,
    so a failed send keeps the typed text instead of losing it."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    # The sendPrompt body ends where the _notifySendBlocked *definition*
    # starts (the method also *calls* _notifySendBlocked earlier).
    send = js.split("sendPrompt() {", 1)[1].split("_notifySendBlocked(text) {", 1)[0]
    socket_idx = send.index("const socket = this._socket(id);")
    # The user message is only pushed after the socket accepted the send.
    push_idx = send.index("store.messages.push(this._newMessage('user', content))")
    assert socket_idx < push_idx
    # And the input is only cleared after the push (main send path).
    clear_idx = send.index("this.input = '';", push_idx)
    assert socket_idx < clear_idx


def test_send_button_disabled_for_all_busy_states():
    """The Send button is disabled for every non-idle status, including
    tool_running (previously enabled while the server dropped mid-turn
    prompts)."""
    html = render_index_html()
    assert ":disabled=\"!input.trim() || status !== 'idle'\"" in html
    # The old binding left tool_running enabled - make sure it is gone
    # (the string below is the exact old :disabled expression; the same
    # status list legitimately survives in the chat-spinner's x-show).
    assert (
        ":disabled=\"!input.trim() || status === 'waiting' || status === 'streaming'\""
        not in html
    )


def test_notify_send_blocked_dispatches_toast_event():
    """_notifySendBlocked renders feedback via the existing toast channel."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    assert "_notifySendBlocked(text)" in js
    assert "CustomEvent('janito-toast'" in js
    assert "kind: 'error'" in js
