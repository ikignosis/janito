"""
WebSocket streaming helpers for the chat router.

Extracted from :mod:`janito.web.backend.routers.chat` so the router module
stays focused on the session CRUD endpoints, the ``chat_websocket`` loop and
the one-shot SSE endpoint.
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from janito.tooling.prompting import set_prompt_handler

from ..events import event_to_dict
from ..prompts import PromptRegistry, WebPromptHandler
from ..session import ConversationSession, SessionManager

logger = logging.getLogger(__name__)


async def _send_session_greeting(websocket: WebSocket) -> None:
    """Greet the client with a tools summary (web counterpart of the CLI's
    startup "N tools active, M skipped" line \u2014 #10)."""
    from janito.tooling.tools_registry import get_all_tools
    from janito.tools import get_skipped_tools

    active_tools = get_all_tools()
    skipped_tools = get_skipped_tools()
    await websocket.send_json(
        {
            "type": "session_start",
            "active_tools": len(active_tools),
            "skipped_tools": len(skipped_tools),
            "skipped": skipped_tools,
        }
    )


async def _read_client_message(websocket: WebSocket) -> dict | None:
    """Read and parse one client frame.

    Returns ``None`` on disconnect, ``{}`` on invalid JSON (already
    reported to the client), or the parsed message dict.
    """
    raw = await websocket.receive_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
        return {}


async def _await_cancel(
    websocket: WebSocket,
    pending_prompts: list[str],
    prompt_registry: PromptRegistry | None = None,
) -> bool:
    """Wait for a ``{"type": "cancel"}`` message from the client.

    Any ``{"type": "prompt"}`` message that arrives while a turn is in
    flight is appended to ``pending_prompts`` instead of being silently
    discarded, so the main loop can process it once the current turn ends.
    This prevents a submission from being lost when the client sends a new
    message while a response is still streaming or a tool is running.

    ``{"type": "prompt_answer", ...}`` messages answer an in-browser
    question raised by an interactive tool (the AskUser tool): they are
    forwarded to ``prompt_registry`` so the worker thread blocked in
    ``prompt_user()`` wakes up with the answer, and the loop keeps reading.

    Returns ``True`` when a cancel message is received, ``False`` when the
    socket disconnects.
    """
    while True:
        try:
            raw = await websocket.receive_text()
        except WebSocketDisconnect:
            return False
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "prompt_answer" and prompt_registry is not None:
            prompt_registry.resolve(msg.get("prompt_id", ""), msg.get("answer", ""))
            continue
        if msg.get("type") == "cancel":
            return True
        if msg.get("type") == "prompt":
            content = (msg.get("content") or "").strip()
            if content:
                pending_prompts.append(content)


def _rollback(session: ConversationSession) -> None:
    """Truncate history back to the pre-turn checkpoint.

    Removes the user message and any partial assistant/tool messages
    appended during the aborted turn, mirroring the shell's Ctrl+C /
    error behaviour.
    """
    del session.messages[session.history_checkpoint :]


async def _stream_to_websocket(
    websocket: WebSocket,
    content: str,
    messages: list[dict],
    config,
    prompt_registry: PromptRegistry | None = None,
):
    """Run ``stream_prompt`` and forward every event to the client.

    When a ``prompt_registry`` is provided (web mode), an in-browser prompt
    handler is installed for the duration of the turn: interactive tools
    (the AskUser tool) present their question as a non-blocking inline card
    in the chat instead of reading stdin. The handler is installed through a
    context variable so the worker thread that executes the tool
    (``asyncio.to_thread``) sees it, and it is scoped to this turn's task.
    """
    # Imported lazily from the chat router so tests that monkeypatch
    # ``chat.stream_prompt`` keep working (the name is looked up in that
    # module's namespace at call time).
    from .chat import stream_prompt

    if prompt_registry is not None:
        set_prompt_handler(
            WebPromptHandler(
                websocket=websocket,
                loop=asyncio.get_running_loop(),
                registry=prompt_registry,
            )
        )
    async for event in stream_prompt(
        prompt=content,
        messages=messages,
        config=config,
        use_mcp=True,
    ):
        await websocket.send_json(event_to_dict(event))


async def _run_turn(
    session: ConversationSession,
    websocket: WebSocket,
    content: str,
    config,
    pending_prompts: list[str],
    prompt_registry: PromptRegistry | None = None,
) -> None:
    """Stream one prompt, racing the client's cancel request.

    A checkpoint is taken before the turn so that both a client cancel and
    an unexpected error can roll the conversation back to a known-good
    state (see :func:`_rollback`).  Prompts that arrive while this turn is
    running are collected into ``pending_prompts`` (see
    :func:`_await_cancel`).
    """
    # Checkpoint before the turn begins (before this turn's user message).
    session.history_checkpoint = len(session.messages)

    stream_task = asyncio.ensure_future(
        _stream_to_websocket(
            websocket, content, session.messages, config, prompt_registry
        )
    )
    cancel_task = asyncio.ensure_future(
        _await_cancel(websocket, pending_prompts, prompt_registry)
    )
    done, pending = await asyncio.wait(
        {stream_task, cancel_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    # The turn is over (finished, cancelled, errored or the socket
    # disconnected): wake any tool thread still blocked on an in-browser
    # question so it returns an empty answer instead of hanging forever.
    if prompt_registry is not None:
        prompt_registry.cancel_all()

    # Always clean up the task that didn't finish first.
    for task in pending:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    # Client requested an abort -> roll back and confirm.
    if cancel_task in done and not cancel_task.cancelled() and cancel_task.result():
        logger.info("[ws] client cancelled stream for session=%s", session.session_id)
        _rollback(session)
        await websocket.send_json({"type": "cancelled"})
        return

    # The stream finished (normally or with an error). Re-raise any stream
    # exception so the caller logs it and rolls back.
    if stream_task in done and not stream_task.cancelled():
        exc = stream_task.exception()
        if exc:
            raise exc


async def _run_prompt_turn(
    session: ConversationSession,
    websocket: WebSocket,
    content: str,
    config,
    pending_prompts: list[str],
    sessions: SessionManager,
    prompt_registry: PromptRegistry | None = None,
) -> None:
    """Run one prompt turn with the shared error handling.

    Persists the finished turn on success (normal completion or client
    cancel \u2014 the latter already rolled back to the checkpoint); on an
    unexpected error it rolls the history back to the checkpoint and reports
    the failure to the client, mirroring the shell's behaviour.  Any prompts
    queued while this turn was running stay in ``pending_prompts`` for the
    caller to drain.
    """
    try:
        await _run_turn(
            session, websocket, content, config, pending_prompts, prompt_registry
        )
        sessions.persist(session)
    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.exception("Error during stream_prompt")
        # Roll back to the checkpoint so a failed turn leaves the
        # conversation context clean for the next prompt.
        _rollback(session)
        sessions.persist(session)  # mirror the rolled-back history
        await websocket.send_json({"type": "error", "message": f"Server error: {e!s}"})
