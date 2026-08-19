"""The tool-call leg of one agentic turn.

Given the assembled tool calls from a streamed response, this module
appends the assistant message, executes each tool (capturing ``report_*``
progress), appends the tool-result messages, and yields the corresponding
events — all in the order the client expects.
"""

import json
import logging

from ..events import AgentEvent, ToolCallEvent, ToolResultEvent
from .tooling import execute_tool, get_tool_permissions, is_mcp_tool

logger = logging.getLogger(__name__)


async def run_tool_turn(
    tool_calls_list: list[dict],
    full_content: str | None,
    messages: list[dict],
    use_mcp: bool,
    thought_parts: list[dict] | None = None,
):
    """Execute one turn's tool calls, mutating ``messages`` and yielding events.

    Args:
        tool_calls_list: The assembled tool calls (OpenAI wire format).
        full_content: The assistant text produced alongside the calls.
        messages: The conversation history (mutated in place).
        use_mcp: Whether MCP tools may be executed.
        thought_parts: Native Gemini thought blocks (text + signature) to
            keep on the assistant message so stateless follow-up turns resend
            them verbatim.  ``None`` (other API types) omits the key.

    Yields:
        ToolCallEvent, ToolProgressEvent*, ToolResultEvent  (per tool)

    ``messages`` ends with the assistant(tool_calls) message followed by one
    tool message per call, ready for the next loop iteration.
    """
    assistant_msg: dict = {
        "role": "assistant",
        "content": full_content or None,
        "tool_calls": tool_calls_list,
    }
    if thought_parts:
        assistant_msg["thought_parts"] = thought_parts
    messages.append(assistant_msg)

    for tc in tool_calls_list:
        tool_name = tc["function"]["name"]
        try:
            tool_args = json.loads(tc["function"]["arguments"])
        except json.JSONDecodeError:
            tool_args = {}
        tool_call_id = tc["id"]

        logger.info(f"Web tool call: {tool_name}({tool_args})")

        permissions = ""
        if not is_mcp_tool(tool_name):
            try:
                permissions = get_tool_permissions(tool_name)
            except Exception:
                permissions = ""

        yield ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments=tool_args,
            permissions=permissions,
        )

        result, progress_events, error, exec_ms = await execute_tool(
            tool_call_id,
            tool_name,
            tool_args,
            use_mcp,
        )

        # Yield captured progress events (report_* output)
        for pe in progress_events:
            yield pe

        yield ToolResultEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            result=result,
            error=error,
            execution_time_ms=exec_ms,
        )

        messages.append(
            {
                "tool_call_id": tool_call_id,
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result)
                if not isinstance(result, str)
                else result,
            }
        )


__all__ = ["run_tool_turn", "AgentEvent"]
