import attr
from typing import Any, ClassVar
from janito.event_bus.event import Event


@attr.s(auto_attribs=True, kw_only=True)
class ToolEvent(Event):
    """
    Base class for events related to tool calls (external or internal tools).
    Includes tool name and request ID for correlation.
    """

    category: ClassVar[str] = "tool"
    tool_name: str
    request_id: str


@attr.s(auto_attribs=True, kw_only=True)
class ToolCallStarted(ToolEvent):
    """
    Event indicating that a tool call has started.
    Contains the arguments passed to the tool.
    """

    arguments: Any


@attr.s(auto_attribs=True, kw_only=True)
class ToolCallFinished(ToolEvent):
    """
    Event indicating that a tool call has finished.
    Contains the result returned by the tool.
    """

    result: Any


@attr.s(auto_attribs=True, kw_only=True)
class ToolRunError(ToolEvent):
    """
    Event indicating that an error occurred during tool execution (for event bus, not exception handling).
    """

    error: str
    exception: Exception = None
    arguments: Any = None


@attr.s(auto_attribs=True, kw_only=True)
class ToolCallError(ToolEvent):
    """
    Event indicating that the tool could not be called (e.g., tool not found, invalid arguments, or invocation failure).
    This is distinct from ToolRunError, which is for errors during execution after the tool has started running.
    """

    error: str
    exception: Exception = None
    arguments: Any = None
