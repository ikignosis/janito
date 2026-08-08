"""Chat endpoints: session CRUD + WebSocket streaming.

The WebSocket handler is intentionally a thin dispatcher: connection setup,
greeting, and the per-turn cancel/rollback machinery live in small helpers
so the main loop reads top to bottom.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..agent import stream_prompt
from ..events import event_to_dict
from ..session import ConversationSession, SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_sessions(request: Request) -> SessionManager:
    return request.app.state.sessions


def _get_config(request: Request):
    return request.app.state.config


# ---------------------------------------------------------------------------
# WebSocket helpers
# ---------------------------------------------------------------------------


async def _send_session_greeting(websocket: WebSocket) -> None:
    """Greet the client with a tools summary (web counterpart of the CLI's
    startup "N tools active, M skipped" line — #10)."""
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


async def _await_cancel(websocket: WebSocket, pending_prompts: list[str]) -> bool:
    """Wait for a ``{"type": "cancel"}`` message from the client.

    Any ``{"type": "prompt"}`` message that arrives while a turn is in
    flight is appended to ``pending_prompts`` instead of being silently
    discarded, so the main loop can process it once the current turn ends.
    This prevents a submission from being lost when the client sends a new
    message while a response is still streaming or a tool is running.

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
    websocket: WebSocket, content: str, messages: list[dict], config
):
    """Run ``stream_prompt`` and forward every event to the client."""
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
        _stream_to_websocket(websocket, content, session.messages, config)
    )
    cancel_task = asyncio.ensure_future(_await_cancel(websocket, pending_prompts))
    done, pending = await asyncio.wait(
        {stream_task, cancel_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

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
) -> None:
    """Run one prompt turn with the shared error handling.

    Persists the finished turn on success (normal completion or client
    cancel — the latter already rolled back to the checkpoint); on an
    unexpected error it rolls the history back to the checkpoint and reports
    the failure to the client, mirroring the shell's behaviour.  Any prompts
    queued while this turn was running stay in ``pending_prompts`` for the
    caller to drain.
    """
    try:
        await _run_turn(session, websocket, content, config, pending_prompts)
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


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


@router.post("/sessions")
async def create_session(request: Request):
    """Create a new conversation session."""
    sessions = _get_sessions(request)
    session = sessions.create()
    return session.to_summary()


@router.get("/sessions")
async def list_sessions(request: Request):
    """List active sessions."""
    sessions = _get_sessions(request)
    return {"sessions": [s.to_summary() for s in sessions.list_sessions()]}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get a session's full history."""
    sessions = _get_sessions(request)
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"detail": "Session not found"}, status_code=404)
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a session."""
    sessions = _get_sessions(request)
    ok = sessions.delete(session_id)
    if not ok:
        return JSONResponse({"detail": "Session not found"}, status_code=404)
    return {"deleted": session_id}


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, request: Request):
    """Rename a session."""
    sessions = _get_sessions(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    title = body.get("title", "")
    if sessions.set_title(session_id, title):
        return {"session_id": session_id, "title": title}
    return JSONResponse({"detail": "Session not found"}, status_code=404)


# ---------------------------------------------------------------------------
# WebSocket streaming
# ---------------------------------------------------------------------------


async def _accept_session(
    websocket: WebSocket, session_id: str
) -> ConversationSession | None:
    """Accept the socket and resolve its session, or close with an error."""
    logger.warning(
        "[ws] handshake received session=%s client=%s", session_id, websocket.client
    )
    await websocket.accept()
    logger.warning("[ws] accepted session=%s", session_id)

    sessions: SessionManager = websocket.app.state.sessions
    session = sessions.get(session_id)
    if not session:
        logger.warning(
            "[ws] session NOT FOUND: %s (known=%s)",
            session_id,
            [s.session_id for s in sessions.list_sessions()],
        )
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return None
    return session


async def _handle_restart(
    session: ConversationSession,
    sessions: SessionManager,
    session_id: str,
    websocket: WebSocket,
) -> None:
    """Restart the session (clear history) and confirm to the client."""
    session.restart()
    sessions.persist(session)  # mirror the cleared history to disk
    await websocket.send_json({"type": "restarted"})


def _maybe_auto_title(
    sessions: SessionManager,
    session_id: str,
    session: ConversationSession,
    content: str,
) -> None:
    """Auto-title the session from the first user prompt."""
    if session.title == "New conversation":
        sessions.set_title(session_id, content[:60])


async def _process_prompt(
    session: ConversationSession,
    websocket: WebSocket,
    config,
    content: str,
    pending_prompts: list[str],
    sessions: SessionManager,
) -> None:
    """Process one user prompt, draining any prompts queued meanwhile.

    Prompts that arrive while a turn is running are queued by
    ``_await_cancel`` (instead of being silently discarded) and are
    processed once the current turn finishes, so a submission is never
    lost mid-stream.
    """
    _maybe_auto_title(sessions, session.session_id, session, content)
    await _run_prompt_turn(
        session, websocket, content, config, pending_prompts, sessions
    )
    for extra in pending_prompts:
        _maybe_auto_title(sessions, session.session_id, session, extra)
        await _run_prompt_turn(
            session, websocket, extra, config, pending_prompts, sessions
        )


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """Bidirectional streaming chat over WebSocket.

    Protocol (JSON messages):
      Client -> Server:  {"type": "prompt"|"restart"|"cancel", ...}
      Server -> Client:  {"type": "token"|"reasoning"|"tool_call"|...}
    """
    session = await _accept_session(websocket, session_id)
    if session is None:
        return

    await _send_session_greeting(websocket)

    sessions: SessionManager = websocket.app.state.sessions
    config = websocket.app.state.config

    try:
        while True:
            msg = await _read_client_message(websocket)
            if msg is None:  # disconnect
                break
            msg_type = msg.get("type")
            if msg_type == "restart":
                await _handle_restart(session, sessions, session_id, websocket)
                continue
            if msg_type != "prompt":
                continue  # ignore unknown message types (could be pings)

            content = (msg.get("content") or "").strip()
            if not content:
                await websocket.send_json({"type": "error", "message": "Empty prompt"})
                continue

            pending_prompts: list[str] = []
            await _process_prompt(
                session, websocket, config, content, pending_prompts, sessions
            )
    except WebSocketDisconnect:
        logger.debug(f"WebSocket client disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# One-shot SSE endpoint (alternative to the WebSocket)
# ---------------------------------------------------------------------------


@router.post("/prompt")
async def one_shot_prompt(request: Request):
    """One-shot Server-Sent-Events streaming endpoint (alternative to WS).

    Body: {"session_id": "...", "content": "..."}
    Returns an ``text/event-stream`` response.
    """
    from fastapi.responses import StreamingResponse

    sessions = _get_sessions(request)
    config = _get_config(request)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    session_id = body.get("session_id")
    content = (body.get("content") or "").strip()
    if not session_id or not content:
        return JSONResponse(
            {"detail": "session_id and content are required"}, status_code=400
        )

    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"detail": "Session not found"}, status_code=404)

    async def sse():
        try:
            async for event in stream_prompt(content, session.messages, config):
                payload = json.dumps(event_to_dict(event))
                yield f"data: {payload}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Persist whatever the turn left in the conversation (success or
            # error) so the one-shot path keeps sessions on disk too.
            sessions.persist(session)

    return StreamingResponse(sse(), media_type="text/event-stream")
