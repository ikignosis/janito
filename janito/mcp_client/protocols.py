"""
MCP protocol implementation - JSON-RPC message handling and parsing.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors."""


class RPCError(MCPError):
    """JSON-RPC error from the server."""

    def __init__(self, error: dict[str, Any]):
        self.code = error.get("code", -1)
        self.message = error.get("message", "Unknown error")
        self.data = error.get("data")
        super().__init__(f"RPC Error {self.code}: {self.message}")


class ProtocolVersionError(MCPError):
    """Server returned unexpected or missing protocol version."""


class ConnectionError(MCPError):
    """Failed to connect to MCP server."""


class RequestTimeoutError(MCPError):
    """Request timed out waiting for response."""


def build_request(request_id: int, method: str, params: dict = None) -> dict:
    """
    Build a JSON-RPC request message.

    Args:
        request_id: Unique identifier for the request
        method: The RPC method name
        params: Optional parameters for the method

    Returns:
        JSON-RPC request dict
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


def build_notification(method: str, params: dict = None) -> dict:
    """
    Build a JSON-RPC notification (no response expected).

    Args:
        method: The notification method name
        params: Optional parameters

    Returns:
        JSON-RPC notification dict
    """
    return {"jsonrpc": "2.0", "method": method, "params": params or {}}


def serialize_message(message: dict) -> str:
    """Serialize a message to JSON with newline terminator."""
    return json.dumps(message) + "\n"


def parse_message(data: str) -> dict | None:
    """
    Parse a JSON-RPC message from string.

    Args:
        data: Raw JSON string

    Returns:
        Parsed message dict or None if invalid
    """
    try:
        return json.loads(data.strip())
    except json.JSONDecodeError:
        return None


def extract_result(response: dict) -> dict:
    """
    Extract result from a JSON-RPC response.

    Args:
        response: JSON-RPC response dict

    Returns:
        The 'result' field

    Raises:
        RPCError: If response contains an error
    """
    if "error" in response:
        raise RPCError(response["error"])

    if "result" not in response:
        raise MCPError("Response missing 'result' field")

    return response["result"]


# Protocol constants
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "janito"
CLIENT_VERSION = "0.1.0"


def get_initialize_params() -> dict:
    """Get standard initialize request parameters."""
    return {
        "protocolVersion": DEFAULT_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
    }


def validate_initialize_response(result: dict) -> str:
    """
    Validate and extract protocol version from initialize response.

    Args:
        result: The result dict from initialize response

    Returns:
        The protocol version string

    Raises:
        ProtocolVersionError: If version is missing
    """
    version = result.get("protocolVersion")
    if not version:
        raise ProtocolVersionError("Server did not return protocol version")
    return version
