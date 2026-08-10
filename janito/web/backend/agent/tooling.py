"""Tool discovery (built-in + MCP) and execution for the web agent.

The tools registry, MCP manager and usage-tracking helpers are always
present within the package, so they are imported directly (no defensive
fallbacks).

Tool *execution* is shared with the CLI loop: the synchronous core
(:func:`janito.tooling.executor.run_tool`) does the routing, usage/used-
files/changes tracking and failure shaping, and captures ``report_*``
output through a progress callback.  This module wraps it in a thread and
converts the captured output into ``ToolProgressEvent``s for the browser.
"""

import asyncio
import logging

from janito.mcp_manager import get_mcp_manager
from janito.tooling.executor import (
    is_mcp_tool as is_mcp_tool,  # re-exported for turn.py
)
from janito.tooling.executor import run_tool
from janito.tooling.tools_registry import get_all_tool_schemas
from janito.tooling.tools_registry import (
    get_tool_permissions as get_tool_permissions,  # re-exported for turn.py
)
from janito.tooling.used_files import (
    reset_used_files as reset_used_files,  # re-exported for loop.py
)

from ..events import ToolProgressEvent

logger = logging.getLogger(__name__)


async def resolve_tools(config, tools: list[dict] | None, use_mcp: bool) -> list[dict]:
    """Resolve the tool schemas to hand to the model for this session.

    - ``config.no_tools`` -> empty list.
    - ``tools`` explicitly provided -> use as-is.
    - Otherwise auto-discover built-in tools plus (optionally) MCP tools.
    """
    if config.no_tools:
        return []

    if tools is not None:
        return tools

    mcp_tools: list[dict] = []
    if use_mcp:
        mcp_manager = get_mcp_manager()
        try:
            await asyncio.to_thread(mcp_manager.load_services)
            mcp_tools = await asyncio.to_thread(mcp_manager.get_all_tools)
            logger.info(
                f"Loaded {len(mcp_tools)} MCP tools from "
                f"{len(mcp_manager.connected_services)} services"
            )
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")

    built_in_tools = get_all_tool_schemas()
    return built_in_tools + mcp_tools


async def execute_tool(
    tool_call_id: str, tool_name: str, tool_args: dict, use_mcp: bool
):
    """Execute a single tool call, capturing report_* output as progress events.

    Returns a tuple ``(result_dict, progress_events, error, exec_time_ms)``.
    The tool runs in a thread via the shared :func:`run_tool` core; the
    progress callback receives every ``report_*`` line (tools are
    synchronous, so the handler sees them in the same thread) and converts
    it into a ``ToolProgressEvent``.
    """
    progress_events: list[ToolProgressEvent] = []

    def handler(level: str, message: str, end: str):
        progress_events.append(
            ToolProgressEvent(
                tool_call_id=tool_call_id,
                level=level,
                message=message,
            )
        )

    result, error, exec_time_ms = await asyncio.to_thread(
        run_tool, tool_name, tool_args, use_mcp, progress=handler
    )
    return result, progress_events, error, exec_time_ms
