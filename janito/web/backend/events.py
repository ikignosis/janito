"""Event dataclasses emitted by the headless agentic loop.

Each event maps to one WebSocket message sent to the browser.  Every event
carries its own ``to_dict()`` so the wire format lives right next to the
data it serializes (adding a field is a one-file change).
:func:`event_to_dict` is a thin dispatcher kept for existing callers.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Union


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


@dataclass
class TokenEvent:
    """Streamed text delta."""

    content: str

    type: ClassVar[str] = "token"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "content": self.content}


@dataclass
class ReasoningEvent:
    """Thinking / reasoning delta."""

    content: str

    type: ClassVar[str] = "reasoning"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "content": self.content}


@dataclass
class ToolCallEvent:
    """The model wants to call a tool."""

    tool_call_id: str
    tool_name: str
    arguments: dict
    permissions: str = ""  # e.g. "r", "w", "x", "rwx"

    type: ClassVar[str] = "tool_call"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": self.tool_call_id,
            "name": self.tool_name,
            "args": self.arguments,
            "permissions": self.permissions,
        }


@dataclass
class ToolResultEvent:
    """A tool finished executing."""

    tool_call_id: str
    tool_name: str
    result: Any
    error: str | None = None
    execution_time_ms: int | None = None

    type: ClassVar[str] = "tool_result"

    def to_dict(self) -> dict[str, Any]:
        result = self.result
        if isinstance(result, dict) and result.get("success") is False:
            result = _safe_result(result)
        return {
            "type": self.type,
            "id": self.tool_call_id,
            "name": self.tool_name,
            "result": _safe_result(result),
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ToolProgressEvent:
    """Intermediate tool output (report_* calls inside tool execution)."""

    tool_call_id: str
    level: str  # "start"|"progress"|"output"|"diff"|"result"|"error"|"warning"|"info"
    message: str  # "output" = raw subprocess stdout/stderr (monospace in UI)

    type: ClassVar[str] = "tool_progress"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": self.tool_call_id,
            "level": self.level,
            "message": self.message,
        }


@dataclass
class WaitingEvent:
    """The API is processing, no tokens yet."""

    phase: str  # "initial" | "after_tools"

    type: ClassVar[str] = "waiting"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "phase": self.phase}


@dataclass
class UsageEvent:
    """Token usage (final chunk)."""

    total: int = 0
    input: int = 0
    output: int = 0
    cached: int = 0
    max_tokens: int | None = None

    type: ClassVar[str] = "usage"

    def to_dict(self) -> dict[str, Any]:
        d = {
            "type": self.type,
            "total": self.total,
            "input": self.input,
            "output": self.output,
            "cached": self.cached,
        }
        if self.max_tokens is not None:
            d["max_tokens"] = self.max_tokens
        return d


@dataclass
class DoneEvent:
    """Conversation turn complete."""

    full_content: str
    message_count: int

    type: ClassVar[str] = "done"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "content": self.full_content,
            "message_count": self.message_count,
        }


@dataclass
class ErrorEvent:
    """An error occurred during the turn."""

    message: str

    type: ClassVar[str] = "error"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "message": self.message}


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
    """Convert an agent event to a JSON-serializable dict for WebSocket send.

    Each event dataclass knows how to serialize itself via ``to_dict()``;
    unknown event types degrade gracefully instead of raising.
    """
    to_dict = getattr(event, "to_dict", None)
    if to_dict is not None:
        return to_dict()
    # Unknown event type — ignore gracefully
    return {"type": "unknown"}
