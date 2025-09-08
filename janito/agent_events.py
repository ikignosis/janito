import attr
from typing import Any, ClassVar, Optional
from janito.event_bus.event import Event


@attr.s(auto_attribs=True, kw_only=True)
class AgentEvent(Event):
    """
    Base class for events related to an agent.
    Includes agent name for identification.
    """

    category: ClassVar[str] = "agent"
    agent_name: Optional[str] = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentInitialized(AgentEvent):
    """Emitted when an agent is initialized."""
    pass


@attr.s(auto_attribs=True, kw_only=True)
class AgentChatStarted(AgentEvent):
    """Emitted when an agent starts a chat session."""
    prompt: Optional[str] = None
    messages: Optional[list] = None
    role: Optional[str] = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentChatFinished(AgentEvent):
    """Emitted when an agent completes a chat session."""
    result: Any = None
    loop_count: int = 0


@attr.s(auto_attribs=True, kw_only=True)
class AgentProcessingResponse(AgentEvent):
    """Emitted when an agent is processing a response."""
    response: Any = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentToolCallStarted(AgentEvent):
    """Emitted when an agent starts processing a tool call."""
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    arguments: Any = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentToolCallFinished(AgentEvent):
    """Emitted when an agent completes processing a tool call."""
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    result: Any = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentWaitingForResponse(AgentEvent):
    """Emitted when an agent is waiting for a response from the LLM API."""
    pass


@attr.s(auto_attribs=True, kw_only=True)
class AgentReceivedResponse(AgentEvent):
    """Emitted when an agent receives a response from the LLM API."""
    response: Any = None


@attr.s(auto_attribs=True, kw_only=True)
class AgentShutdown(AgentEvent):
    """Emitted when an agent is shutting down."""
    pass