"""
MCP-aware Tools Registry - Extended tools registry with MCP support.

This module extends the existing tools registry to include MCP tools
alongside built-in tools, providing a unified interface.

MCP tools are gathered at runtime from the MCP manager (see
``janito.mcp_manager``), which tracks the currently connected MCP
services and exposes their tools as OpenAI function-calling schemas.
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any

from ..mcp_manager import get_mcp_manager
from .tools_registry import get_all_tool_permissions as get_builtin_permissions
from .tools_registry import get_all_tool_schemas as get_builtin_schemas
from .tools_registry import get_all_tools as get_builtin_tools
from .tools_registry import get_tool_by_name as get_builtin_tool_by_name

logger = logging.getLogger(__name__)


def get_mcp_tool_schemas() -> list[dict[str, Any]]:
    """
    Get OpenAI function-calling schemas for all connected MCP tools.

    Returns:
        List of tool schemas; empty when no MCP services are connected.
    """
    manager = get_mcp_manager()
    if manager is None or not manager.connected_services:
        return []

    try:
        return manager.get_all_tools()
    except Exception:
        logger.warning("Failed to collect schemas from connected MCP services")
        return []


def _make_mcp_tool_callable(func_spec: dict[str, Any]) -> Callable:
    """
    Wrap an MCP tool as a callable mirroring the built-in tool wrappers.

    The returned callable exposes ``__name__``, ``__doc__`` and
    ``__signature__`` so it can be used interchangeably with built-in
    tool wrappers (e.g. by ``get_function_schema``).
    """
    name = func_spec["name"]
    parameters = func_spec.get("parameters", {})
    if not isinstance(parameters, dict):
        parameters = {}
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))

    def mcp_tool(**kwargs: Any) -> Any:
        return get_mcp_manager().call_tool(name, kwargs)

    mcp_tool.__name__ = name
    mcp_tool.__doc__ = func_spec.get("description") or ""
    mcp_tool.__signature__ = inspect.Signature(
        [
            inspect.Parameter(
                p,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=inspect.Parameter.empty if p in required else None,
                annotation=inspect.Parameter.empty,
            )
            for p in properties
        ]
    )
    return mcp_tool


def get_all_mcp_tools() -> dict[str, Callable]:
    """
    Collect the tools of all connected MCP services as callables.

    Returns:
        Mapping of prefixed tool name (e.g. ``service_tool``) to callable;
        empty when no MCP services are connected.
    """
    manager = get_mcp_manager()
    if manager is None or not manager.connected_services:
        return {}

    try:
        service_tools = manager.get_all_tools()
    except Exception:
        logger.warning("Failed to collect tools from connected MCP services")
        return {}

    tools: dict[str, Callable] = {}
    for schema in service_tools:
        try:
            func_spec = schema["function"]
            name = func_spec["name"]
        except (KeyError, TypeError):
            continue
        try:
            tools[name] = _make_mcp_tool_callable(func_spec)
        except Exception:
            logger.warning("Failed to wrap MCP tool '%s'", name)
    return tools


def get_all_tools_with_mcp(
    mcp_tools: dict[str, Callable] | None = None
) -> dict[str, Callable]:
    """
    Get all tools including built-in and MCP tools.

    Args:
        mcp_tools: MCP tools dictionary. If None, gathers the tools of the
            currently connected MCP services.

    Returns:
        Combined dictionary of all tools
    """
    tools = get_builtin_tools()

    if mcp_tools is not None:
        tools.update(mcp_tools)
    else:
        tools.update(get_all_mcp_tools())

    return tools


def get_all_tool_schemas_with_mcp(
    mcp_schemas: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """
    Get all tool schemas including built-in and MCP tools.

    Args:
        mcp_schemas: MCP tool schemas. If None, gathers the schemas of the
            currently connected MCP services.

    Returns:
        Combined list of all tool schemas
    """
    schemas = get_builtin_schemas()

    if mcp_schemas is not None:
        schemas.extend(mcp_schemas)
    else:
        schemas.extend(get_mcp_tool_schemas())

    return schemas


def get_all_tool_permissions_with_mcp(
    mcp_permissions: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Get all tool permissions including built-in and MCP tools.

    Args:
        mcp_permissions: MCP tool permissions. If None, MCP tools are
            assumed to require no specific permission flags (the manager
            does not track per-tool permissions).

    Returns:
        Combined dictionary of all tool permissions
    """
    permissions = get_builtin_permissions()

    if mcp_permissions is not None:
        permissions.update(mcp_permissions)

    return permissions


def get_tool_by_name_with_mcp(
    name: str, mcp_tools: dict[str, Callable] | None = None
) -> Callable:
    """
    Get a tool by name, searching both built-in and MCP tools.

    Args:
        name: Tool name
        mcp_tools: MCP tools dictionary. If None, gathers the tools of the
            currently connected MCP services.

    Returns:
        Tool callable

    Raises:
        KeyError: If tool not found
    """
    # Try built-in tools first
    try:
        return get_builtin_tool_by_name(name)
    except KeyError:
        pass

    # Try MCP tools
    all_mcp = mcp_tools if mcp_tools is not None else get_all_mcp_tools()

    if name in all_mcp:
        return all_mcp[name]

    raise KeyError(f"Tool '{name}' not found in built-in or MCP tools")


def is_mcp_tool(name: str) -> bool:
    """
    Check if a tool is an MCP tool (served by a connected MCP service).

    Args:
        name: Tool name (MCP tools carry their service name as a prefix)

    Returns:
        True if the tool comes from a connected MCP service
    """
    manager = get_mcp_manager()
    if manager is None:
        return False

    return manager.get_service_for_tool(name) is not None


def get_tool_source(name: str) -> str:
    """
    Get the source of a tool (builtin or mcp).

    Args:
        name: Tool name

    Returns:
        "builtin" or "mcp" or "unknown"
    """
    # Check built-in
    try:
        get_builtin_tool_by_name(name)
        return "builtin"
    except KeyError:
        pass

    # Check MCP
    if is_mcp_tool(name):
        return "mcp"

    return "unknown"


# Backwards compatibility - these will include MCP tools when available
def get_all_tools() -> dict[str, Callable]:
    """Get all available tools (built-in + MCP)."""
    return get_all_tools_with_mcp()


def get_all_tool_schemas() -> list[dict[str, Any]]:
    """Get all tool schemas (built-in + MCP)."""
    return get_all_tool_schemas_with_mcp()


def get_all_tool_permissions() -> dict[str, str]:
    """Get all tool permissions (built-in + MCP)."""
    return get_all_tool_permissions_with_mcp()


def get_tool_by_name(name: str) -> Callable:
    """Get a tool by name (built-in or MCP)."""
    return get_tool_by_name_with_mcp(name)
