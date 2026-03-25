"""
Janito4 - OpenAI CLI with Function Calling Tools

A simple command-line interface to interact with OpenAI-compatible endpoints
with built-in function calling capabilities and MCP (Model Context Protocol) support.
"""

# MCP modules
from .mcp_config import (
    MCP_CONFIG_PATH,
    load_mcp_config,
    save_mcp_config,
    get_service,
    add_service,
    remove_service,
    list_services,
)

from .mcp_client.base import MCPTransport
from .mcp_client.stdio import StdioTransport
from .mcp_client.http import HttpTransport
from .mcp_client.factory import create_transport

from .mcp_manager import (
    MCPManager,
    get_mcp_manager,
    shutdown_mcp_manager,
)

__all__ = [
    # MCP Config
    "MCP_CONFIG_PATH",
    "load_mcp_config",
    "save_mcp_config",
    "get_service",
    "add_service",
    "remove_service",
    "list_services",
    # MCP Client
    "MCPTransport",
    "StdioTransport",
    "HttpTransport",
    "create_transport",
    # MCP Manager
    "MCPManager",
    "get_mcp_manager",
    "shutdown_mcp_manager",
]
