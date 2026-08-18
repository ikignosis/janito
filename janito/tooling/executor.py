"""
ToolExecutor - executes the tool calls the model makes during an agent turn.

This module centralises the tool-execution logic that was previously embedded
in the CLI agent loop (``janito/openai_client/completions_api.py``): routing each tool
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
import time
from typing import Any

from ..mcp_manager import MCPManager, get_mcp_manager
from .changes import record_change
from .reporter import set_report_handler
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


def run_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    use_mcp: bool = True,
    *,
    mcp_manager: MCPManager | None = None,
    progress: Any = None,
) -> tuple[Any, str | None, int]:
    """Execute a single tool call and return ``(result, error, exec_time_ms)``.

    This is the **shared tool-execution core** used by both agent loops:

    - the CLI ``ToolExecutor.execute_tool_call`` (called synchronously),
    - the web agent loop, which runs it in a thread via
      ``asyncio.to_thread`` (``janito.web.backend.agent.tooling.execute_tool``).

    It routes the call to the MCP manager or the built-in tools registry,
    tracks usage / used files / changes (best-effort, never raises), and
    converts a failing call into a structured ``{"success": False, ...}``
    result instead of raising, so a failing tool never aborts the agent
    loop.  When ``progress`` is given, it is installed as the report handler
    for the duration of the call, so every ``report_*`` line the tool emits
    is forwarded to it (web mode); the CLI passes ``None`` and keeps the
    default Rich console output.

    Args:
        tool_name: The tool to invoke.
        tool_args: The arguments to pass to the tool.
        use_mcp: Whether MCP routing is enabled. When ``True``, MCP tools
            (resolved via :func:`is_mcp_tool`) go to the manager; otherwise
            every call goes to the built-in registry.
        mcp_manager: The MCP manager used to route MCP tool calls. When
            ``None``, the global manager (see :func:`get_mcp_manager`) is
            used lazily.
        progress: Optional ``(level, message, end)`` report callback.

    Returns:
        A tuple ``(result, error, exec_time_ms)``: ``result`` is the raw
        tool result (a ``{"success": False, "error": ...}`` dict on
        failure), ``error`` is ``None`` on success, and ``exec_time_ms`` is
        the wall-clock execution time.
    """
    record_tool_use(tool_name)
    if progress is not None:
        set_report_handler(progress)
    start = time.time()
    error: str | None = None
    result: Any = None
    try:
        if use_mcp and is_mcp_tool(tool_name):
            manager = mcp_manager or get_mcp_manager()
            result = manager.call_tool(tool_name, tool_args)
        else:
            tool_fn = get_tool_by_name(tool_name)
            result = tool_fn(**tool_args)
    except Exception as e:  # noqa: BLE001 - a failing tool must not stop the loop
        logger.error(f"Tool {tool_name} failed: {e}")
        error = str(e)
        result = {
            "success": False,
            "error": f"Tool execution failed: {e!s}",
        }
    finally:
        if progress is not None:
            set_report_handler(None)  # restore default (Rich console)

    # Track which files this successful call touched (only when the first
    # argument is "filepath"; best-effort, never raises). A tool signals
    # logical failure via a falsy "success" key in its result dict; such
    # calls are not tracked.
    if error is None and not (
        isinstance(result, dict) and result.get("success") is False
    ):
        record_used_file(tool_name, tool_args)
        # Log the execution to ./.janito/changes.jsonl so the /changes
        # command can replay it (best-effort, never raises).
        record_change(tool_name, tool_args)

    return result, error, int((time.time() - start) * 1000)


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
        self, full_content: str, tool_calls_map: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """Build the assistant message carrying the model's tool calls.

        The model streams tool-call *deltas* split across many chunks; the
        stream consumer assembles them into ``tool_calls_map`` (index ->
        ``{id, name, arguments}``, plus any provider-specific extras such as
        Gemini's ``extra_content.google.thought_signature``). This method
        converts that map into the assistant message the API expects in the
        conversation history, preserving those extras so they can be echoed
        back verbatim on the next turn.

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
            tool_call = {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
            # Preserve provider-specific extras (e.g. Gemini's
            # ``extra_content.google.thought_signature``) when echoing the
            # call back in the conversation history; dropping them makes
            # Gemini 3.x reject the next request with a 400 "Function call is
            # missing a thought_signature in functionCall parts" error.
            extra_content = tc.get("extra_content")
            if extra_content:
                tool_call["extra_content"] = extra_content
            tool_calls_list.append(tool_call)
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

        # The shared core does the routing, usage/used-files/changes tracking
        # and failure shaping (see run_tool).
        tool_result, error, _ = run_tool(
            tool_name,
            tool_args,
            use_mcp=True,
            mcp_manager=self.mcp_manager,
        )
        if error:
            print(f"\u274c Tool error: {tool_name} - {error}", file=sys.stderr)

        return {
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(tool_result),
        }


__all__ = [
    "ToolExecutor",
    "is_mcp_tool",
    "run_tool",
]
