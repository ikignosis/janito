"""
MCP transport using HTTP with SSE (Server-Sent Events).
"""

import json
import logging
import threading
from typing import Dict, Any, Optional

from .base import MCPTransport
from .protocols import (
    build_request,
    build_notification,
    extract_result,
    get_initialize_params,
    validate_initialize_response,
    MCPError
)

logger = logging.getLogger(__name__)

# Lazy import for requests - it's an optional dependency
try:
    import requests
except ImportError:
    requests = None


class HttpTransport(MCPTransport):
    """
    MCP transport using HTTP with SSE (Server-Sent Events).
    
    Communicates with a remote MCP server via HTTP, handling
    both standard JSON responses and Server-Sent Events.
    """
    
    def __init__(self, url: str, headers: Dict[str, str] = None):
        """
        Initialize HTTP transport.
        
        Args:
            url: The MCP server URL
            headers: Optional headers to include in requests
            
        Raises:
            ImportError: If requests library is not installed
        """
        if requests is None:
            raise ImportError(
                "requests library is required for HTTP transport. "
                "Install with: pip install requests"
            )
        
        self.url = url
        self.headers = headers or {}
        self._connected = False
        self._error: Optional[str] = None
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._lock = threading.Lock()
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self) -> bool:
        """Send initialize request to the MCP server."""
        try:
            result = self.send_request("initialize", get_initialize_params())
            validate_initialize_response(result)
            
            self._connected = True
            logger.info(f"Connected to MCP server: {self.url}")
            
            # Send initialized notification
            self.send_notification("initialized", {})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._error = str(e)
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._connected = False
        self._session_id = None
        logger.info(f"Disconnected from MCP server: {self.url}")
    
    def send_request(self, method: str, params: Dict = None) -> Any:
        """
        Send a JSON-RPC request and return the response.
        
        Handles both standard JSON responses and SSE responses.
        
        Args:
            method: RPC method name
            params: Optional parameters
            
        Returns:
            The result from the server
        """
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
        
        request = build_request(request_id, method, params)
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id
        
        try:
            response = requests.post(
                self.url,
                json=request,
                headers=headers,
                timeout=30,
                stream=True  # Important for SSE
            )
            response.raise_for_status()
            
            # Store session ID if provided
            if "MCP-Session-Id" in response.headers:
                self._session_id = response.headers["MCP-Session-Id"]
                logger.debug(f"Got MCP session ID: {self._session_id}")
            
            # Parse and extract result
            result = self._parse_response(response, request_id)
            return extract_result(result)
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    def _parse_response(self, response, request_id: int) -> Dict:
        """
        Parse response content, handling SSE format.
        
        Args:
            response: The requests Response object
            request_id: The request ID we're waiting for
            
        Returns:
            The parsed JSON-RPC response
        """
        content_type = response.headers.get("Content-Type", "")
        
        if self._is_sse_response(content_type):
            return self._parse_sse_response(response, request_id)
        else:
            return response.json()
    
    def _is_sse_response(self, content_type: str) -> bool:
        """Check if response is Server-Sent Events format."""
        return "text/event-stream" in content_type or "text/plain" in content_type
    
    def _parse_sse_response(self, response, request_id: int) -> Dict:
        """
        Parse Server-Sent Events response.
        
        Args:
            response: The requests Response object
            request_id: The request ID we're waiting for
            
        Returns:
            The parsed JSON-RPC response
        """
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # Parse SSE format: "data: {...}"
            if line.startswith("data:"):
                data = line[5:].strip()
                if not data:
                    continue
                
                try:
                    message = json.loads(data)
                    
                    # Check for matching JSON-RPC response
                    if "id" in message and message["id"] == request_id:
                        return message
                    
                    # Check for result in message
                    if "result" in message:
                        return message
                        
                except json.JSONDecodeError:
                    continue
        
        raise MCPError("No valid response found in SSE stream")
    
    def send_notification(self, method: str, params: Dict = None) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            method: Notification method name
            params: Optional parameters
        """
        notification = build_notification(method, params)
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id
        
        try:
            requests.post(
                self.url,
                json=notification,
                headers=headers,
                timeout=5
            )
        except Exception as e:
            logger.debug(f"Notification send failed (ignored): {e}")
