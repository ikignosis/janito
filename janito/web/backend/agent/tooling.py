"""Tool discovery (built-in + MCP) and execution for the web agent.

The tools registry, MCP manager and usage-tracking helpers are always
present within the package, so they are imported directly (no defensive
fallbacks).
"""

import asyncio
import logging
import time

from ..events import ToolProgressEvent

logger = logging.getLogger(__name__)

# --- MCP manager ---
from janito.mcp_manager import get_mcp_manager

# Changes tracking (best-effort, never fails). Successful tool calls whose
# first argument is "filepath" are logged to ./.janito/changes.jsonl so the
# /changes command can replay them.
from janito.tooling.changes import record_change

# Reporter handler for capturing tool output in web mode
from janito.tooling.reporter import set_report_handler

# --- Tools registry ---
from janito.tooling.tools_registry import get_all_tool_schemas, get_tool_by_name
from janito.tooling.tools_registry import (
    get_tool_permissions as get_tool_permissions,  # re-exported for turn.py
)

# Tool usage tracking (best-effort, never fails)
from janito.tooling.tools_usage import record_tool_use

# Used-files tracking (best-effort, never fails)
from janito.tooling.used_files import record_used_file
from janito.tooling.used_files import (
    reset_used_files as reset_used_files,  # re-exported for loop.py
)


def is_mcp_tool(tool_name: str) -> bool:
    """Check if a tool name is an MCP tool (has service_ prefix)."""
    mcp_manager = get_mcp_manager()
    if mcp_manager:
        return mcp_manager.get_service_for_tool(tool_name) is not None
    return False


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
    The tool runs in a thread (tools are synchronous); ``contextvars`` ensure
    the report handler is visible inside the thread and isolated per-task.
    """
    # Track the tool usage (best-effort, never raises)
    record_tool_use(tool_name)

    progress_events: list[ToolProgressEvent] = []

    def handler(level: str, message: str, end: str):
        progress_events.append(
            ToolProgressEvent(
                tool_call_id=tool_call_id,
                level=level,
                message=message,
            )
        )

    start = time.time()
    set_report_handler(handler)
    error: str | None = None
    result = None
    try:
        if use_mcp and is_mcp_tool(tool_name):
            mcp_manager = get_mcp_manager()
            result = await asyncio.to_thread(
                mcp_manager.call_tool, tool_name, tool_args
            )
        else:
            tool_fn = get_tool_by_name(tool_name)
            result = await asyncio.to_thread(tool_fn, **tool_args)
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        error = str(e)
        result = {
            "success": False,
            "error": f"Tool execution failed: {e!s}",
        }
    finally:
        set_report_handler(None)  # restore default (Rich console)

    # Track which files this successful call touched (only when the first
    # argument is "filepath"; best-effort, never raises). Skip calls that
    # raised or that returned a logical failure ({"success": False}).
    if error is None and not (
        isinstance(result, dict) and result.get("success") is False
    ):
        record_used_file(tool_name, tool_args)
        # Log the execution to ./.janito/changes.jsonl so the /changes command
        # can replay it (best-effort, never raises).
        record_change(tool_name, tool_args)

    exec_time_ms = int((time.time() - start) * 1000)
    return result, progress_events, error, exec_time_ms
