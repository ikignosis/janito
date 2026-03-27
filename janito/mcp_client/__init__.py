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
from .stdio import StdioTransport
from .http import HttpTransport
from .factory import create_transport

# Protocol exports for error handling and advanced usage
from .protocols import (
    MCPError,
    RPCError,
    ProtocolVersionError,
    ConnectionError as MCPConnectionError,
    RequestTimeoutError,
    build_request,
    build_notification,
    parse_message,
    serialize_message,
    extract_result,
)

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
