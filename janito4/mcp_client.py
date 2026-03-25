"""
MCP client module for communicating with MCP servers.

Supports two transport types:
- stdio: Local process communication via stdin/stdout
- http: Remote server communication via HTTP/SSE
"""

import json
import logging
import subprocess
import threading
import queue
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """Abstract base class for MCP transports."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the MCP server."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        pass
    
    @abstractmethod
    def send_request(self, method: str, params: Dict = None) -> Any:
        """Send a JSON-RPC request and return the response."""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[Dict]:
        """List available tools from the server."""
        pass
    
    @abstractmethod
    def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool on the server."""
        pass
    
    @abstractmethod
    def list_prompts(self) -> List[Dict]:
        """List available prompts from the server."""
        pass
    
    @abstractmethod
    def get_prompt(self, name: str, arguments: Dict = None) -> Any:
        """Get a prompt from the server with arguments."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the transport is connected."""
        pass


class StdioTransport(MCPTransport):
    """MCP transport using stdio (local subprocess)."""
    
    def __init__(self, command: str, env: Dict[str, str] = None):
        """
        Initialize stdio transport.
        
        Args:
            command: The command to execute (e.g., "python -m mcp.server")
            env: Optional environment variables to pass to the subprocess
        """
        self.command = command
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._response_queues: Dict[int, queue.Queue] = {}
        self._notification_thread: Optional[threading.Thread] = None
        self._running = False
        self._error: Optional[str] = None
    
    @property
    def is_connected(self) -> bool:
        return self.process is not None and self.process.poll() is None
    
    def connect(self) -> bool:
        """Start the subprocess and initialize the MCP connection."""
        if self.is_connected:
            return True
        
        try:
            # Merge environment variables
            env = {**subprocess.os.environ.copy(), **self.env}
            
            # Start the subprocess
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1
            )
            
            # Start notification handler thread BEFORE sending any requests
            self._running = True
            self._notification_thread = threading.Thread(target=self._read_notifications)
            self._notification_thread.daemon = True
            self._notification_thread.start()
            
            # Give the thread a moment to start
            import time
            time.sleep(0.1)
            
            # Send initialize request
            result = self._send_request_sync("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "janito4",
                    "version": "0.1.0"
                }
            })
            
            if result.get("protocolVersion"):
                logger.info(f"Connected to MCP server: {self.command}")
                
                # Send initialized notification
                self._send_notification("initialized", {})
                
                return True
            else:
                logger.error("Server did not return protocol version")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._error = str(e)
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Terminate the subprocess."""
        self._running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.debug(f"Error during disconnect: {e}")
            self.process = None
        
        # Clear response queues
        self._response_queues.clear()
        logger.info(f"Disconnected from MCP server: {self.command}")
    
    def _read_notifications(self) -> None:
        """Background thread to read notifications from stdout."""
        while self._running and self.is_connected:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                message = json.loads(line.strip())
                
                # Handle notifications (no id field) and responses
                if "id" not in message:
                    # Handle notification
                    method = message.get("method", "")
                    params = message.get("params", {})
                    self._handle_notification(method, params)
                elif message["id"] in self._response_queues:
                    # Route to waiting request
                    self._response_queues[message["id"]].put(message)
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"Error reading from MCP server: {e}")
    
    def _handle_notification(self, method: str, params: Dict) -> None:
        """Handle incoming notifications from the server."""
        logger.debug(f"Received notification: {method}")
    
    def _send_request_sync(self, method: str, params: Dict = None) -> Dict:
        """Send a request and wait for response (blocking)."""
        response = self._send_request_async(method, params)
        
        # Wait for response
        try:
            result_queue = self._response_queues.get(response["id"])
            if result_queue:
                response_message = result_queue.get(timeout=30)
                del self._response_queues[response["id"]]
                
                if "error" in response_message:
                    raise Exception(f"RPC error: {response_message['error']}")
                
                return response_message.get("result", {})
        except queue.Empty:
            raise TimeoutError(f"Request {method} timed out")
        
        return {}
    
    def _send_request_async(self, method: str, params: Dict = None) -> Dict:
        """Send a request asynchronously and return immediately."""
        if not self.is_connected:
            raise ConnectionError("Not connected to MCP server")
        
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Create response queue
        self._response_queues[request_id] = queue.Queue()
        
        # Send request
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        logger.debug(f"Sent request: {method}")
        return {"id": request_id}
    
    def _send_notification(self, method: str, params: Dict = None) -> None:
        """Send a notification (no response expected)."""
        if not self.is_connected:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        self.process.stdin.write(json.dumps(notification) + "\n")
        self.process.stdin.flush()
        logger.debug(f"Sent notification: {method}")
    
    def send_request(self, method: str, params: Dict = None) -> Any:
        """Send a JSON-RPC request and return the response."""
        return self._send_request_sync(method, params)
    
    def list_tools(self) -> List[Dict]:
        """List available tools from the server."""
        try:
            result = self._send_request_sync("tools/list")
            tools = result.get("tools", [])
            logger.debug(f"Listed {len(tools)} tools from MCP server")
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool on the server."""
        result = self._send_request_sync("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return result
    
    def list_prompts(self) -> List[Dict]:
        """List available prompts from the server."""
        try:
            result = self._send_request_sync("prompts/list")
            prompts = result.get("prompts", [])
            logger.debug(f"Listed {len(prompts)} prompts from MCP server")
            return prompts
        except Exception as e:
            logger.error(f"Failed to list prompts: {e}")
            return []
    
    def get_prompt(self, name: str, arguments: Dict = None) -> Any:
        """Get a prompt from the server with arguments."""
        result = self._send_request_sync("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
        return result


class HttpTransport(MCPTransport):
    """MCP transport using HTTP with SSE (Server-Sent Events)."""
    
    def __init__(self, url: str, headers: Dict[str, str] = None):
        """
        Initialize HTTP transport.
        
        Args:
            url: The MCP server URL
            headers: Optional headers to include in requests
        """
        self.url = url
        self.headers = headers or {}
        self._connected = False
        self._error: Optional[str] = None
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._lock = threading.Lock()
        
        # Lazy import requests
        try:
            import requests
            self._requests = requests
        except ImportError:
            raise ImportError("requests library is required for HTTP transport. Install with: pip install requests")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def connect(self) -> bool:
        """Send initialize request to the MCP server."""
        try:
            # Send initialize request
            result = self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "janito4",
                    "version": "0.1.0"
                }
            })
            
            if result.get("protocolVersion"):
                self._connected = True
                logger.info(f"Connected to MCP server: {self.url}")
                
                # Send initialized notification
                self.send_notification("initialized", {})
                
                return True
            else:
                logger.error("Server did not return protocol version")
                return False
                
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
        """Send a JSON-RPC request and return the response (handles SSE)."""
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        # Include session ID if we have one
        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id
        
        try:
            response = self._requests.post(
                self.url,
                json=request,
                headers=headers,
                timeout=30,
                stream=True  # Important for SSE
            )
            response.raise_for_status()
            
            # Extract session ID from response headers if present
            if "MCP-Session-Id" in response.headers:
                self._session_id = response.headers["MCP-Session-Id"]
                logger.debug(f"Got MCP session ID: {self._session_id}")
            
            # Parse SSE response
            result = self._parse_sse_response(response)
            
            return result.get("result", {})
            
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    def _parse_sse_response(self, response) -> Dict:
        """Parse Server-Sent Events response.
        
        Args:
            response: The requests Response object
            
        Returns:
            The parsed JSON result from the response
        """
        content_type = response.headers.get("Content-Type", "")
        
        if "text/event-stream" in content_type or "text/plain" in content_type:
            # SSE response - parse event stream
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                
                # Parse SSE format: "data: {...}"
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        try:
                            message = json.loads(data)
                            
                            # Check for JSON-RPC response
                            if "id" in message and message["id"] == self._request_id:
                                if "error" in message:
                                    raise Exception(f"RPC error: {message['error']}")
                                return message
                            
                            # Check for result in message
                            if "result" in message:
                                return message
                                
                        except json.JSONDecodeError:
                            continue
        else:
            # Regular JSON response
            return response.json()
        
        return {}
    
    def send_notification(self, method: str, params: Dict = None) -> None:
        """Send a notification (no response expected)."""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            **self.headers
        }
        
        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id
        
        try:
            # Fire and forget for notifications
            self._requests.post(
                self.url,
                json=request,
                headers=headers,
                timeout=5
            )
        except Exception as e:
            logger.debug(f"Notification send failed (ignored): {e}")
    
    def list_tools(self) -> List[Dict]:
        """List available tools from the server."""
        try:
            result = self.send_request("tools/list")
            tools = result.get("tools", [])
            logger.debug(f"Listed {len(tools)} tools from MCP server")
            return tools
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool on the server."""
        result = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return result
    
    def list_prompts(self) -> List[Dict]:
        """List available prompts from the server."""
        try:
            result = self.send_request("prompts/list")
            prompts = result.get("prompts", [])
            logger.debug(f"Listed {len(prompts)} prompts from MCP server")
            return prompts
        except Exception as e:
            logger.error(f"Failed to list prompts: {e}")
            return []
    
    def get_prompt(self, name: str, arguments: Dict = None) -> Any:
        """Get a prompt from the server with arguments."""
        result = self.send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
        return result


def create_transport(config: Dict[str, Any]) -> MCPTransport:
    """
    Factory function to create a transport from config.
    
    Args:
        config: Service configuration dict with 'transport' key
        
    Returns:
        MCPTransport instance
        
    Raises:
        ValueError: If transport type is unknown
    """
    transport_type = config.get("transport", "").lower()
    
    if transport_type == "stdio":
        return StdioTransport(
            command=config.get("command", ""),
            env=config.get("env", {})
        )
    elif transport_type == "http":
        return HttpTransport(
            url=config.get("url", ""),
            headers=config.get("headers", {})
        )
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")
