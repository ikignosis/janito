"""Tool discovery (built-in + MCP) and execution for the web agent.

All imports of optional janito subsystems (tools registry, MCP manager,
usage tracking) are guarded so the agent keeps working when they are
unavailable — mirroring ``janito/openai_client/client.py`` behaviour.
"""

import asyncio
import logging
import time

from ..events import ToolProgressEvent

logger = logging.getLogger(__name__)

# --- Tools registry (lazy-safe — mirrors client.py behaviour) ---
try:
    from janito.tooling.tools_registry import (
        get_all_tool_schemas,
        get_tool_by_name,
        get_tool_permissions,
    )

    TOOLS_AVAILABLE = True
except (ImportError, ValueError):
    TOOLS_AVAILABLE = False

    def get_all_tool_schemas():
        return []

    def get_tool_by_name(name):
        raise NotImplementedError("Tools not available")

    def get_tool_permissions(name):
        return ""


# --- MCP manager ---
try:
    from janito.mcp_manager import get_mcp_manager

    MCP_MANAGER_AVAILABLE = True
except ImportError:
    MCP_MANAGER_AVAILABLE = False

    def get_mcp_manager():
        return None


# Reporter handler for capturing tool output in web mode
from janito.tooling.reporter import set_report_handler

# Tool usage tracking (best-effort, never fails)
try:
    from janito.tooling.tools_usage import record_tool_use
except ImportError:  # pragma: no cover - fallback keeps agent working

    def record_tool_use(name):
        pass


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
    if use_mcp and MCP_MANAGER_AVAILABLE:
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

    built_in_tools = get_all_tool_schemas() if TOOLS_AVAILABLE else []
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

    exec_time_ms = int((time.time() - start) * 1000)
    return result, progress_events, error, exec_time_ms
