"""
ToolExecutor - executes the tool calls the model makes during an agent turn.

This module centralises the tool-execution logic that was previously embedded
in the CLI agent loop (``janito/openai_client/client.py``): routing each tool
call to either the MCP manager or the built-in tools registry, tracking tool
usage / used files / changes, and producing the ``tool``-role messages that
are appended to the conversation history. Failures are converted into
structured error results rather than being raised to the caller, so a failing
tool never aborts the agent loop.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from ..mcp_manager import MCPManager, get_mcp_manager
from .changes import record_change
from .tools_registry import get_tool_by_name
from .tools_usage import record_tool_use
from .used_files import record_used_file

logger = logging.getLogger(__name__)


def is_mcp_tool(tool_name: str) -> bool:
    """Check if a tool name is an MCP tool (has a ``service_`` prefix).

    MCP tools are prefixed with their service name; the manager resolves the
    prefix back to the service that provides the tool.

    Args:
        tool_name: The tool name the model asked to call.

    Returns:
        bool: ``True`` when the tool belongs to a connected MCP service.
    """
    mcp_manager = get_mcp_manager()
    if mcp_manager:
        return mcp_manager.get_service_for_tool(tool_name) is not None
    return False


class ToolExecutor:
    """Execute the tool calls produced by the model during a turn.

    The executor owns the bookkeeping around a single tool invocation: usage
    tracking (``record_tool_use``), routing to the MCP manager or the
    built-in registry, recording used files and changes for successful calls,
    and formatting the ``tool``-role message that is appended to the
    conversation history.

    A failed call never raises: the exception is caught and turned into a
    structured ``{"success": False, "error": ...}`` result so the model can
    see why the tool failed and react accordingly.
    """

    def __init__(self, mcp_manager: MCPManager | None = None) -> None:
        """Create an executor, optionally bound to a specific MCP manager.

        Args:
            mcp_manager: The MCP manager used to route MCP tool calls. When
                ``None`` (the default), the global manager (see
                :func:`janito.mcp_manager.get_mcp_manager`) is used lazily.
        """
        self._mcp_manager = mcp_manager

    @property
    def mcp_manager(self) -> MCPManager:
        """The MCP manager used for routing, resolving lazily if needed."""
        if self._mcp_manager is None:
            self._mcp_manager = get_mcp_manager()
        return self._mcp_manager

    def build_assistant_message(
        self, full_content: str, tool_calls_map: dict[int, dict[str, str]]
    ) -> dict[str, Any]:
        """Build the assistant message carrying the model's tool calls.

        The model streams tool-call *deltas* split across many chunks; the
        stream consumer assembles them into ``tool_calls_map`` (index ->
        ``{id, name, arguments}``). This method converts that map into the
        assistant message the API expects in the conversation history.

        Args:
            full_content: The assistant text produced alongside the calls
                (may be empty), stored as ``None`` in the message when empty.
            tool_calls_map: Map of tool-call index to the assembled
                ``{id, name, arguments}`` dicts.

        Returns:
            dict: An ``assistant``-role message with a ``tool_calls`` list,
            ordered by call index.
        """
        tool_calls_list = []
        for idx in sorted(tool_calls_map):
            tc = tool_calls_map[idx]
            tool_calls_list.append(
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
            )
        return {
            "role": "assistant",
            "content": full_content or None,
            "tool_calls": tool_calls_list,
        }

    def handle_tool_calls(
        self,
        tool_calls_map: dict[int, dict[str, str]],
        messages: list[dict[str, Any]],
        full_content: str = "",
    ) -> None:
        """Process a full round of model tool calls in one go.

        Builds the assistant message (with ``tool_calls``), appends it to
        ``messages``, executes every call and appends the resulting
        ``tool``-role responses to ``messages``. The caller then continues
        the agent loop to obtain the model's final answer.

        Args:
            tool_calls_map: Map of tool-call index to the assembled
                ``{id, name, arguments}`` dicts.
            messages: The conversation history; mutated in place.
            full_content: Assistant text produced alongside the calls.
        """
        assistant_msg = self.build_assistant_message(full_content, tool_calls_map)
        messages.append(assistant_msg)
        self.execute_tool_calls(assistant_msg["tool_calls"], messages)

    def execute_tool_calls(
        self, tool_calls: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> None:
        """Execute every tool call and append its response to ``messages``.

        Args:
            tool_calls: List of tool-call dicts (as produced by
                :meth:`build_assistant_message`).
            messages: The conversation history; mutated in place.
        """
        for tool_call in tool_calls:
            messages.append(self.execute_tool_call(tool_call))

    def execute_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """Execute a single tool call and return the ``tool``-role message.

        Args:
            tool_call: One tool-call dict with ``id`` and a ``function``
                object carrying ``name`` and ``arguments`` (JSON string).

        Returns:
            dict: A ``tool``-role message whose ``content`` is the JSON
                serialisation of the tool result. On failure the result is
                ``{"success": False, "error": ...}`` and the error is printed
                to stderr; the call never raises.
        """
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        tool_call_id = tool_call["id"]

        logger.info(f"Tool call: {tool_name}({tool_args})")

        # Track the tool usage (best-effort, never raises).
        record_tool_use(tool_name)

        try:
            tool_result = self._run_tool(tool_name, tool_args)
        except Exception as e:  # noqa: BLE001 - a failing tool must not stop the loop
            logger.error(f"Tool {tool_name} failed: {e}")
            tool_result = {
                "success": False,
                "error": f"Tool execution failed: {e!s}",
            }
            print(f"\u274c Tool error: {tool_name} - {e}", file=sys.stderr)

        # Track which files this successful call touched (only when the first
        # argument is "filepath"; best-effort, never raises). A tool signals
        # logical failure via a falsy "success" key in its result dict; such
        # calls are not tracked.
        if not (isinstance(tool_result, dict) and tool_result.get("success") is False):
            record_used_file(tool_name, tool_args)
            # Log the execution to ./janito/changes.jsonl so the /changes
            # command can replay it (best-effort).
            record_change(tool_name, tool_args)

        return {
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(tool_result),
        }

    def _run_tool(self, tool_name: str, tool_args: dict) -> Any:
        """Route a single tool call to the MCP manager or built-in registry.

        Args:
            tool_name: The tool to invoke.
            tool_args: The arguments to pass to the tool.

        Returns:
            Any: The raw tool result (dict for built-in tools, any value for
                MCP tools).

        Raises:
            KeyError: If the tool is not a built-in tool and not handled by a
                connected MCP service.
        """
        if is_mcp_tool(tool_name):
            # Route to MCP manager
            logger.debug(f"Routing MCP tool call: {tool_name}")
            result = self.mcp_manager.call_tool(tool_name, tool_args)
            logger.info(f"MCP tool {tool_name} completed successfully")
            return result

        # Route to built-in tool
        logger.debug(f"Executing built-in tool: {tool_name}")
        tool_function = get_tool_by_name(tool_name)
        result = tool_function(**tool_args)
        logger.info(f"Tool {tool_name} completed successfully")
        return result


__all__ = [
    "ToolExecutor",
    "is_mcp_tool",
]
