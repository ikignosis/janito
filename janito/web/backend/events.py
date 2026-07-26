"""Event dataclasses emitted by the headless agentic loop.

Each event maps to one WebSocket message sent to the browser. The router
serializes them via :func:`event_to_dict`.
"""

from dataclasses import dataclass
from typing import Any, Union


@dataclass
class TokenEvent:
    """Streamed text delta."""

    content: str


@dataclass
class ReasoningEvent:
    """Thinking / reasoning delta."""

    content: str


@dataclass
class ToolCallEvent:
    """The model wants to call a tool."""

    tool_call_id: str
    tool_name: str
    arguments: dict
    permissions: str = ""  # e.g. "r", "w", "x", "rwx"


@dataclass
class ToolResultEvent:
    """A tool finished executing."""

    tool_call_id: str
    tool_name: str
    result: Any
    error: str | None = None
    execution_time_ms: int | None = None


@dataclass
class ToolProgressEvent:
    """Intermediate tool output (report_* calls inside tool execution)."""

    tool_call_id: str
    level: str  # "start"|"progress"|"output"|"result"|"error"|"warning"|"info"
    message: str  # "output" = raw subprocess stdout/stderr (monospace in UI)


@dataclass
class WaitingEvent:
    """The API is processing, no tokens yet."""

    phase: str  # "initial" | "after_tools"


@dataclass
class UsageEvent:
    """Token usage (final chunk)."""

    total: int = 0
    input: int = 0
    output: int = 0
    cached: int = 0


@dataclass
class DoneEvent:
    """Conversation turn complete."""

    full_content: str
    message_count: int


@dataclass
class ErrorEvent:
    """An error occurred during the turn."""

    message: str


AgentEvent = Union[
    TokenEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolResultEvent,
    WaitingEvent,
    ToolProgressEvent,
    UsageEvent,
    DoneEvent,
    ErrorEvent,
]


def event_to_dict(event: AgentEvent) -> dict[str, Any]:
    """Convert an agent event to a JSON-serializable dict for WebSocket send."""
    if isinstance(event, TokenEvent):
        return {"type": "token", "content": event.content}
    if isinstance(event, ReasoningEvent):
        return {"type": "reasoning", "content": event.content}
    if isinstance(event, ToolCallEvent):
        return {
            "type": "tool_call",
            "id": event.tool_call_id,
            "name": event.tool_name,
            "args": event.arguments,
            "permissions": event.permissions,
        }
    if isinstance(event, ToolResultEvent):
        result = event.result
        if isinstance(result, dict) and result.get("success") is False:
            result = _safe_result(result)
        return {
            "type": "tool_result",
            "id": event.tool_call_id,
            "name": event.tool_name,
            "result": _safe_result(result),
            "error": event.error,
            "execution_time_ms": event.execution_time_ms,
        }
    if isinstance(event, ToolProgressEvent):
        return {
            "type": "tool_progress",
            "id": event.tool_call_id,
            "level": event.level,
            "message": event.message,
        }
    if isinstance(event, WaitingEvent):
        return {"type": "waiting", "phase": event.phase}
    if isinstance(event, UsageEvent):
        return {
            "type": "usage",
            "total": event.total,
            "input": event.input,
            "output": event.output,
            "cached": event.cached,
        }
    if isinstance(event, DoneEvent):
        return {
            "type": "done",
            "content": event.full_content,
            "message_count": event.message_count,
        }
    if isinstance(event, ErrorEvent):
        return {"type": "error", "message": event.message}
    # Unknown event type — ignore gracefully
    return {"type": "unknown"}


def _safe_result(result: Any) -> Any:
    """Ensure a tool result is JSON-serializable (for the browser)."""
    if result is None or isinstance(result, (str, int, float, bool)):
        return result
    if isinstance(result, dict):
        try:
            import json

            json.dumps(result)
            return result
        except (TypeError, ValueError):
            return str(result)
    return str(result)
