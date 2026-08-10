"""Contract tests for the in-browser question modal (AskUser tool in web mode).

The AskUser tool's ``prompt_user`` normally reads from stdin; in web mode
there is no console. The backend instead installs a ``WebPromptHandler``
(context variable in ``janito/tooling/prompting``) that presents the
question as a browser modal and blocks the tool's worker thread until the
browser posts the answer back as a ``prompt_answer`` WebSocket frame.

These tests pin down:

1. ``PromptRegistry`` (backend): register / resolve / cancel_all semantics;
2. ``_await_cancel`` (backend) resolves ``prompt_answer`` frames into the
   registry while a turn is running;
3. the full round trip: a tool running in a worker thread (as
   ``asyncio.to_thread``, like the web loop does) asks a question, the
   ``prompt`` frame is sent to the "browser", the registry resolves it, and
   the tool returns the answer;
4. frontend wiring: the ``prompt`` event handler, the ``prompt_answer``
   socket helper, the app-level modal state, and the rendered modal markup.
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
# Backend: PromptRegistry
# ---------------------------------------------------------------------------


def test_registry_register_resolve():
    """register() adds a pending prompt; resolve() stores the answer and
    wakes the waiter; the entry is removed afterwards."""
    from janito.web.backend.prompts import PromptRegistry

    registry = PromptRegistry()
    pending = registry.register("id1", "Question?")
    assert registry.has_pending() is True
    assert pending.answer is None
    assert pending.wait(timeout=0) is False  # not resolved yet

    assert registry.resolve("id1", "Answer") is True
    assert pending.answer == "Answer"
    assert pending.wait(timeout=0) is True  # waiter was woken
    assert registry.has_pending() is False

    # Resolving again is a no-op (the entry was consumed).
    assert registry.resolve("id1", "again") is False


def test_registry_resolve_unknown_is_noop():
    """resolve() of an unknown id returns False (stale prompt_answer)."""
    from janito.web.backend.prompts import PromptRegistry

    registry = PromptRegistry()
    assert registry.resolve("missing", "x") is False


def test_registry_cancel_all_wakes_workers():
    """cancel_all() wakes every waiter with no answer (turn ended)."""
    from janito.web.backend.prompts import PromptRegistry

    registry = PromptRegistry()
    p1 = registry.register("a", "Q1?")
    p2 = registry.register("b", "Q2?")
    assert registry.cancel_all() == 2
    assert p1.cancelled is True
    assert p2.cancelled is True
    assert p1.wait(timeout=0) is True
    assert p2.wait(timeout=0) is True
    assert p1.answer is None
    assert registry.has_pending() is False
    # A third cancel_all finds nothing.
    assert registry.cancel_all() == 0


# ---------------------------------------------------------------------------
# Backend: _await_cancel resolves prompt_answer frames
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
def test_await_cancel_resolves_prompt_answer():
    """A prompt_answer frame during a turn resolves the pending prompt."""
    from janito.web.backend.prompts import PromptRegistry
    from janito.web.backend.routers.chat import _await_cancel

    registry = PromptRegistry()
    pending = registry.register("abc123", "Meaning of life?")

    ws = _FakeWebSocket(
        [
            json.dumps(
                {"type": "prompt_answer", "prompt_id": "abc123", "answer": "42"}
            ),
            json.dumps({"type": "cancel"}),
        ]
    )
    result = asyncio.run(_await_cancel(ws, [], registry))

    assert result is True
    assert pending.answer == "42"
    assert pending.wait(timeout=0) is True
    assert registry.has_pending() is False


@requires_fastapi
def test_await_cancel_continues_after_prompt_answer():
    """Resolving an answer does not end the receive loop: prompts queued
    afterwards are still collected and cancel still works."""
    from janito.web.backend.prompts import PromptRegistry
    from janito.web.backend.routers.chat import _await_cancel

    registry = PromptRegistry()
    ws = _FakeWebSocket(
        [
            json.dumps(
                {"type": "prompt_answer", "prompt_id": "abc123", "answer": "42"}
            ),
            json.dumps({"type": "prompt", "content": "queued"}),
            json.dumps({"type": "cancel"}),
        ]
    )
    pending: list[str] = []
    result = asyncio.run(_await_cancel(ws, pending, registry))

    assert result is True
    assert pending == ["queued"]


@requires_fastapi
def test_await_cancel_without_registry_ignores_prompt_answer():
    """Backwards compat: the 2-arg call (no registry) keeps ignoring
    prompt_answer frames and reading until cancel/disconnect."""
    from janito.web.backend.routers.chat import _await_cancel

    ws = _FakeWebSocket(
        [
            json.dumps({"type": "prompt_answer", "prompt_id": "x", "answer": "y"}),
            json.dumps({"type": "cancel"}),
        ]
    )
    result = asyncio.run(_await_cancel(ws, []))
    assert result is True


# ---------------------------------------------------------------------------
# Backend: full round trip (tool thread -> modal -> answer)
# ---------------------------------------------------------------------------


class _PromptWebSocket:
    """Fake websocket that records sent frames and signals the prompt."""

    def __init__(self):
        self.sent = []
        self._prompt_event = asyncio.Event()

    async def send_json(self, payload):
        self.sent.append(payload)
        if payload.get("type") == "prompt":
            self._prompt_event.set()

    async def wait_for_prompt(self, timeout=2.0):
        await asyncio.wait_for(self._prompt_event.wait(), timeout)

    @property
    def last_prompt(self):
        for payload in reversed(self.sent):
            if payload.get("type") == "prompt":
                return payload
        return None


class _DuplexWebSocket(_PromptWebSocket):
    """Fake websocket for the full turn: records sent frames and blocks on
    receive_text() until the turn's cancel_task is cancelled."""

    def __init__(self):
        super().__init__()
        self._close_event = asyncio.Event()

    async def receive_text(self):
        # No queued frames: keep the connection open (like a real socket)
        # so the turn's race is decided by the stream task completing.
        await self._close_event.wait()
        raise WebSocketDisconnect()

    def close(self):
        self._close_event.set()


@requires_fastapi
def test_web_prompt_handler_round_trip():
    """A tool running in a worker thread (asyncio.to_thread, like the web
    loop) asks a question; the prompt frame reaches the "browser"; resolving
    the registry wakes the thread; the tool returns the answer."""
    from janito.tooling.prompting import set_prompt_handler
    from janito.tools.system.ask_user import AskUser
    from janito.web.backend.prompts import PromptRegistry, WebPromptHandler

    async def scenario():
        registry = PromptRegistry()
        ws = _PromptWebSocket()
        handler = WebPromptHandler(ws, asyncio.get_running_loop(), registry)
        set_prompt_handler(handler)
        try:
            # Run the tool in a worker thread, exactly like the web loop's
            # execute_tool (asyncio.to_thread copies the current context, so
            # the handler installed above is visible to prompt_user).
            task = asyncio.ensure_future(
                asyncio.to_thread(AskUser().run, question="Your name?")
            )
            # The "browser" receives the question…
            await ws.wait_for_prompt(timeout=2.0)
            prompt = ws.last_prompt
            assert prompt["type"] == "prompt"
            assert prompt["question"] == "Your name?"
            assert prompt["prompt_id"]

            # …and answers it (the receive loop's prompt_answer handler).
            assert registry.resolve(prompt["prompt_id"], "  Ada Lovelace  ") is True

            result = await asyncio.wait_for(task, timeout=2.0)
            return result
        finally:
            set_prompt_handler(None)

    result = asyncio.run(scenario())
    assert result["success"] is True
    assert result["answer"] == "Ada Lovelace"  # stripped, like the CLI path


@requires_fastapi
def test_web_prompt_handler_turn_cancel_returns_empty():
    """If the turn ends while the question is pending (cancel_all), the
    worker thread wakes up with an empty answer instead of hanging."""
    from janito.tooling.prompting import set_prompt_handler
    from janito.tools.system.ask_user import AskUser
    from janito.web.backend.prompts import PromptRegistry, WebPromptHandler

    async def scenario():
        registry = PromptRegistry()
        ws = _PromptWebSocket()
        handler = WebPromptHandler(ws, asyncio.get_running_loop(), registry)
        set_prompt_handler(handler)
        try:
            task = asyncio.ensure_future(
                asyncio.to_thread(AskUser().run, question="Are you there?")
            )
            await ws.wait_for_prompt(timeout=2.0)
            # The turn was cancelled / the socket died: wake every waiter.
            assert registry.cancel_all() == 1
            result = await asyncio.wait_for(task, timeout=2.0)
            return result
        finally:
            set_prompt_handler(None)

    result = asyncio.run(scenario())
    assert result["success"] is True
    assert result["answer"] == ""


@requires_fastapi
def test_run_turn_in_browser_prompt_round_trip(monkeypatch):
    """Full chat.py plumbing: ``_stream_to_websocket`` installs the prompt
    handler, a tool running in a worker thread blocks on the question, the
    receive-loop resolution wakes it, and the turn completes normally with
    the answer in the streamed tool result."""
    import janito.web.backend.routers.chat as chat_mod
    from janito.agent.events import DoneEvent, ToolResultEvent
    from janito.web.backend.prompts import PromptRegistry
    from janito.web.backend.session import ConversationSession

    async def fake_stream_prompt(prompt, messages, config, tools=None, use_mcp=True):
        from janito.tools.system.ask_user import AskUser

        # Mirror run_tool_turn/execute_tool: the tool runs in a worker
        # thread whose prompt_user blocks on the in-browser question.
        result = await asyncio.to_thread(AskUser().run, question="Your name?")
        yield ToolResultEvent(tool_call_id="call_1", tool_name="AskUser", result=result)
        yield DoneEvent(full_content="done", message_count=len(messages))

    monkeypatch.setattr(chat_mod, "stream_prompt", fake_stream_prompt)

    async def scenario():
        registry = PromptRegistry()
        ws = _DuplexWebSocket()
        session = ConversationSession(session_id="s1")

        turn = asyncio.ensure_future(
            chat_mod._run_turn(session, ws, "hi", object(), [], registry)
        )
        # The "browser" receives the question…
        await ws.wait_for_prompt(timeout=2.0)
        prompt = ws.last_prompt
        assert prompt["type"] == "prompt"
        assert prompt["question"] == "Your name?"

        # …and answers it (exactly what _await_cancel does for a
        # prompt_answer frame).
        assert registry.resolve(prompt["prompt_id"], "Ada") is True

        await asyncio.wait_for(turn, timeout=2.0)

        sent_types = [p.get("type") for p in ws.sent]
        assert "prompt" in sent_types
        assert "tool_result" in sent_types
        assert "done" in sent_types
        tool_result = next(p for p in ws.sent if p.get("type") == "tool_result")
        assert tool_result["result"]["success"] is True
        assert tool_result["result"]["answer"] == "Ada"
        # The streamed events went out on the same connection.
        assert ws.last_prompt is not None

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Frontend wiring (static checks, no server needed)
# ---------------------------------------------------------------------------


def test_chat_events_handles_prompt_event():
    """chatEvents.js records the pending question and surfaces the modal."""
    js = (FRONTEND / "js" / "chatEvents.js").read_text(encoding="utf-8")
    assert "prompt(c) {" in js
    assert "pendingPrompt" in js
    assert "janito-prompt" in js
    # The event carries the ids the backend expects.
    assert "prompt_id: c.event.prompt_id" in js
    assert "question: c.event.question" in js


def test_chat_component_routes_prompt_answer():
    """chat.js projects pendingPrompt and routes the answer to the socket."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    assert "pendingPrompt: null" in js
    assert "this.pendingPrompt = store.pendingPrompt;" in js
    assert "_submitPromptAnswer" in js
    assert "janito-prompt-answer" in js
    assert "sendPromptAnswer(prompt_id, answer)" in js


def test_websocket_has_send_prompt_answer():
    """websocket.js exposes the prompt_answer frame helper."""
    js = (FRONTEND / "js" / "websocket.js").read_text(encoding="utf-8")
    assert "sendPromptAnswer(promptId, answer) {" in js
    assert "'prompt_answer'" in js
    assert "prompt_id: promptId" in js


def test_app_component_renders_modal_state():
    """app.js owns the modal state and submit/dismiss actions."""
    js = (FRONTEND / "js" / "app.js").read_text(encoding="utf-8")
    assert "promptModal: null" in js
    assert "promptAnswer: ''" in js
    assert "submitPromptAnswer()" in js
    assert "dismissPrompt()" in js
    assert "'janito-prompt'" in js
    assert "janito-prompt-dismiss" in js


def test_index_html_renders_prompt_modal():
    """The composed page renders the question modal in the root scope."""
    html = render_index_html()
    assert 'x-if="promptModal"' in html
    assert 'class="modal-card prompt-modal"' in html
    assert 'id="prompt-modal-input"' in html
    assert "renderPromptQuestion(promptModal.question)" in html
    assert '@keydown.enter.prevent="submitPromptAnswer()"' in html


def test_drawers_css_styles_prompt_modal():
    """drawers.css styles the question modal."""
    css = (FRONTEND / "css" / "drawers.css").read_text(encoding="utf-8")
    assert ".prompt-modal {" in css
    assert ".prompt-question {" in css
    assert ".prompt-input {" in css
