"""
Helpers for handling tool calls in conversation.
"""

from janito.agent.tool_registry import handle_tool_call
from .conversation_exceptions import MaxRoundsExceededError
from janito.agent.runtime_config import runtime_config


def handle_tool_calls(tool_calls, message_handler=None):
    max_tools = runtime_config.get("max_tools", None)
    tool_calls_made = 0
    tool_responses = []
    for tool_call in tool_calls:
        if max_tools is not None and tool_calls_made >= max_tools:
            raise MaxRoundsExceededError(
                f"Maximum number of tool calls ({max_tools}) reached in this chat session."
            )
        result = handle_tool_call(tool_call, message_handler=message_handler)
        tool_responses.append({"tool_call_id": tool_call.id, "content": result})
        tool_calls_made += 1
    return tool_responses
