"""Chat endpoints: session CRUD + WebSocket streaming."""

import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..agent import stream_prompt
from ..events import event_to_dict
from ..session import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_sessions(request: Request) -> SessionManager:
    return request.app.state.sessions


def _get_config(request: Request):
    return request.app.state.config


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


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """Bidirectional streaming chat over WebSocket.

    Protocol (JSON messages):
      Client -> Server:  {"type": "prompt", "content": "..."}
      Server -> Client:  {"type": "token"|"reasoning"|"tool_call"|...}
    """
    logger.warning(
        "[ws] handshake received session=%s client=%s", session_id, websocket.client
    )
    await websocket.accept()
    logger.warning("[ws] accepted session=%s", session_id)

    sessions: SessionManager = websocket.app.state.sessions
    config = websocket.app.state.config

    session = sessions.get(session_id)
    if not session:
        logger.warning(
            "[ws] session NOT FOUND: %s (known=%s)",
            session_id,
            [s.session_id for s in sessions.list_sessions()],
        )
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    # Greet the client with a tools summary so the UI can render it at the
    # start of the session (web counterpart of the CLI startup line — #10).
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

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if msg.get("type") != "prompt":
                # Ignore unknown message types (could be pings)
                continue

            content = (msg.get("content") or "").strip()
            if not content:
                await websocket.send_json({"type": "error", "message": "Empty prompt"})
                continue

            # Auto-title the session from the first user prompt
            if session.title == "New conversation":
                sessions.set_title(session_id, content[:60])

            try:
                async for event in stream_prompt(
                    prompt=content,
                    messages=session.messages,
                    config=config,
                    use_mcp=True,
                ):
                    await websocket.send_json(event_to_dict(event))
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.exception("Error during stream_prompt")
                await websocket.send_json(
                    {"type": "error", "message": f"Server error: {e!s}"}
                )
    except WebSocketDisconnect:
        logger.debug(f"WebSocket client disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


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

    return StreamingResponse(sse(), media_type="text/event-stream")
