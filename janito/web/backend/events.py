"""Web agent event types — re-exported from the shared agent event layer.

The event dataclasses now live in :mod:`janito.agent.events` (the shared
per-API adapter layer used by both agent loops); this module re-exports
them under the historical web path so the routers, the loop and existing
tests keep their import paths.
"""

from janito.agent.events import (  # noqa: F401
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    ImageEvent,
    ReasoningEvent,
    TokenEvent,
    ToolCallEvent,
    ToolProgressEvent,
    ToolResultEvent,
    UsageEvent,
    WaitingEvent,
    _safe_result,
    event_to_dict,
)

__all__ = [
    "AgentEvent",
    "DoneEvent",
    "ErrorEvent",
    "ImageEvent",
    "ReasoningEvent",
    "TokenEvent",
    "ToolCallEvent",
    "ToolProgressEvent",
    "ToolResultEvent",
    "UsageEvent",
    "WaitingEvent",
    "_safe_result",
    "event_to_dict",
]
