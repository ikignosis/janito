"""
MCP Transport base class and abstract interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """
    Abstract base class for MCP transports.
    
    A transport handles the underlying communication with an MCP server,
    whether that's via stdio (local subprocess) or HTTP/SSE (remote).
    
    Subclasses must implement:
    - connect/disconnect lifecycle
    - is_connected property
    - send_request for JSON-RPC calls
    - send_notification for one-way messages
    """
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the transport is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the MCP server and perform handshake.
        
        Sends initialize request and waits for response,
        then sends 'initialized' notification.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        pass
    
    @abstractmethod
    def send_request(self, method: str, params: Dict = None) -> Any:
        """
        Send a JSON-RPC request and return the response.
        
        Args:
            method: The RPC method name
            params: Optional method parameters
            
        Returns:
            The result from the server
            
        Raises:
            ConnectionError: If not connected
            TimeoutError: If request times out
            RPCError: If server returns an error
        """
        pass
    
    @abstractmethod
    def send_notification(self, method: str, params: Dict = None) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            method: The notification method name
            params: Optional parameters
        """
        pass
    
    def list_tools(self) -> List[Dict]:
        """
        List available tools from the server.
        
        Returns:
            List of tool definitions
        """
        try:
            result = self.send_request("tools/list")
            tools = result.get("tools", [])
            logger.debug(f"Listed {len(tools)} tools from MCP server")
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    def call_tool(self, name: str, arguments: Dict) -> Any:
        """
        Call a tool on the server.
        
        Args:
            name: Tool name to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        result = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return result
