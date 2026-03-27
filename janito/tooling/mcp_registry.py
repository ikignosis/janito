"""
MCP-aware Tools Registry - Extended tools registry with MCP support.

This module extends the existing tools registry to include MCP tools
alongside built-in tools, providing a unified interface.
"""

import logging
from typing import Dict, Any, List, Callable, Optional

from .tools_registry import (
    get_all_tools as get_builtin_tools,
    get_all_tool_schemas as get_builtin_schemas,
    get_all_tool_permissions as get_builtin_permissions,
    get_tool_by_name as get_builtin_tool_by_name,
    get_function_schema,
)

logger = logging.getLogger(__name__)


def get_all_tools_with_mcp(mcp_tools: Optional[Dict[str, Callable]] = None) -> Dict[str, Callable]:
    """
    Get all tools including built-in and MCP tools.
    
    Args:
        mcp_tools: MCP tools dictionary. If None, tries to get from MCP integration.
        
    Returns:
        Combined dictionary of all tools
    """
    tools = get_builtin_tools()
    
    if mcp_tools is not None:
        tools.update(mcp_tools)
    else:
        try:
            from ..mcp.integration import get_mcp_tools
            tools.update(get_mcp_tools())
        except ImportError:
            pass
    
    return tools


def get_all_tool_schemas_with_mcp(mcp_schemas: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Get all tool schemas including built-in and MCP tools.
    
    Args:
        mcp_schemas: MCP tool schemas. If None, tries to get from MCP integration.
        
    Returns:
        Combined list of all tool schemas
    """
    schemas = get_builtin_schemas()
    
    if mcp_schemas is not None:
        schemas.extend(mcp_schemas)
    else:
        try:
            from ..mcp.integration import get_mcp_tool_schemas
            schemas.extend(get_mcp_tool_schemas())
        except ImportError:
            pass
    
    return schemas


def get_all_tool_permissions_with_mcp(mcp_permissions: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get all tool permissions including built-in and MCP tools.
    
    Args:
        mcp_permissions: MCP tool permissions. If None, tries to get from MCP integration.
        
    Returns:
        Combined dictionary of all tool permissions
    """
    permissions = get_builtin_permissions()
    
    if mcp_permissions is not None:
        permissions.update(mcp_permissions)
    else:
        try:
            from ..mcp.integration import get_mcp_tool_permissions
            permissions.update(get_mcp_tool_permissions())
        except ImportError:
            pass
    
    return permissions


def get_tool_by_name_with_mcp(name: str, mcp_tools: Optional[Dict[str, Callable]] = None) -> Callable:
    """
    Get a tool by name, searching both built-in and MCP tools.
    
    Args:
        name: Tool name
        mcp_tools: MCP tools dictionary
        
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
    all_mcp = mcp_tools or {}
    if not all_mcp:
        try:
            from ..mcp.integration import get_mcp_tools
            all_mcp = get_mcp_tools()
        except ImportError:
            pass
    
    if name in all_mcp:
        return all_mcp[name]
    
    raise KeyError(f"Tool '{name}' not found in built-in or MCP tools")


def is_mcp_tool(name: str) -> bool:
    """
    Check if a tool is an MCP tool.
    
    Args:
        name: Tool name
        
    Returns:
        True if the tool is from MCP
    """
    try:
        from ..mcp.integration import get_mcp_tool_by_name
        return get_mcp_tool_by_name(name) is not None
    except ImportError:
        return False


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
def get_all_tools() -> Dict[str, Callable]:
    """Get all available tools (built-in + MCP)."""
    return get_all_tools_with_mcp()


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas (built-in + MCP)."""
    return get_all_tool_schemas_with_mcp()


def get_all_tool_permissions() -> Dict[str, str]:
    """Get all tool permissions (built-in + MCP)."""
    return get_all_tool_permissions_with_mcp()


def get_tool_by_name(name: str) -> Callable:
    """Get a tool by name (built-in or MCP)."""
    return get_tool_by_name_with_mcp(name)
