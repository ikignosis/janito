"""
MCP Client Module

Communication with MCP (Model Context Protocol) servers.

Supports two transport types:
- stdio: Local process communication via stdin/stdout
- http: Remote server communication via HTTP/SSE

Usage:
    from janito.mcp_client import create_transport

    # From config
    config = {"transport": "stdio", "command": "python -m mcp.server"}
    transport = create_transport(config)

    if transport.connect():
        tools = transport.list_tools()
        result = transport.call_tool("tool_name", {"arg": "value"})
        transport.disconnect()
"""

# Core exports
from .base import MCPTransport
from .factory import create_transport
from .http import HttpTransport

# Protocol exports for error handling and advanced usage
from .protocols import ConnectionError as MCPConnectionError
from .protocols import (
    MCPError,
    ProtocolVersionError,
    RequestTimeoutError,
    RPCError,
    build_notification,
    build_request,
    extract_result,
    parse_message,
    serialize_message,
)
from .stdio import StdioTransport

__all__ = [
    # Main classes
    "MCPTransport",
    "StdioTransport",
    "HttpTransport",
    "create_transport",
    # Protocol utilities
    "MCPError",
    "RPCError",
    "ProtocolVersionError",
    "MCPConnectionError",
    "RequestTimeoutError",
    "build_request",
    "build_notification",
    "parse_message",
    "serialize_message",
    "extract_result",
]
