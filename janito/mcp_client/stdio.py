"""
MCP transport using stdio (local subprocess communication).
"""

import json
import logging
import subprocess
import threading
import time
import queue
from typing import Dict, Any, Optional

from .base import MCPTransport
from .protocols import (
    build_request,
    build_notification,
    serialize_message,
    parse_message,
    extract_result,
    get_initialize_params,
    validate_initialize_response,
    RequestTimeoutError,
    MCPError
)

logger = logging.getLogger(__name__)


class StdioTransport(MCPTransport):
    """
    MCP transport using stdio (local subprocess).
    
    Communicates with an MCP server by spawning a subprocess
    and exchanging JSON-RPC messages via stdin/stdout.
    """
    
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
            # Start the subprocess
            env = {**subprocess.os.environ.copy(), **self.env}
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1
            )
            
            # Start notification handler thread
            self._running = True
            self._notification_thread = threading.Thread(target=self._read_loop)
            self._notification_thread.daemon = True
            self._notification_thread.start()
            
            # Brief pause for thread startup
            time.sleep(0.1)
            
            # Send initialize request
            result = self._send_request_sync("initialize", get_initialize_params())
            validate_initialize_response(result)
            
            logger.info(f"Connected to MCP server: {self.command}")
            
            # Send initialized notification
            self._send_notification("initialized", {})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._error = str(e)
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Terminate the subprocess and clean up."""
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
        
        self._response_queues.clear()
        logger.info(f"Disconnected from MCP server: {self.command}")
    
    def _read_loop(self) -> None:
        """Background thread to read messages from stdout."""
        while self._running and self.is_connected:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                message = parse_message(line)
                if message is None:
                    continue
                
                self._dispatch_message(message)
                
            except Exception as e:
                logger.debug(f"Error reading from MCP server: {e}")
    
    def _dispatch_message(self, message: Dict) -> None:
        """
        Route a message to appropriate handler.
        
        Args:
            message: Parsed JSON-RPC message
        """
        if "id" not in message:
            # Notification - no response needed
            self._handle_notification(
                message.get("method", ""),
                message.get("params", {})
            )
        elif message["id"] in self._response_queues:
            # Response to a request we sent
            self._response_queues[message["id"]].put(message)
    
    def _handle_notification(self, method: str, params: Dict) -> None:
        """Handle incoming notification from the server."""
        logger.debug(f"Received notification: {method}")
    
    def _send_request_sync(self, method: str, params: Dict = None) -> Dict:
        """
        Send a request and wait for response (blocking).
        
        Args:
            method: RPC method name
            params: Optional parameters
            
        Returns:
            The result from the server
            
        Raises:
            RequestTimeoutError: If response not received in time
            MCPError: If server returns an error
        """
        response_id = self._send_request_async(method, params)
        
        try:
            result_queue = self._response_queues.get(response_id)
            if result_queue:
                response_message = result_queue.get(timeout=30)
                del self._response_queues[response_id]
                return extract_result(response_message)
        except queue.Empty:
            raise RequestTimeoutError(f"Request {method} timed out")
        
        return {}
    
    def _send_request_async(self, method: str, params: Dict = None) -> int:
        """
        Send a request asynchronously.
        
        Args:
            method: RPC method name
            params: Optional parameters
            
        Returns:
            The request ID
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to MCP server")
        
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
        
        request = build_request(request_id, method, params)
        self._response_queues[request_id] = queue.Queue()
        
        self.process.stdin.write(serialize_message(request))
        self.process.stdin.flush()
        
        logger.debug(f"Sent request: {method}")
        return request_id
    
    def _send_notification(self, method: str, params: Dict = None) -> None:
        """Send a notification (no response expected)."""
        if not self.is_connected:
            return
        
        notification = build_notification(method, params)
        self.process.stdin.write(serialize_message(notification))
        self.process.stdin.flush()
        logger.debug(f"Sent notification: {method}")
    
    def send_request(self, method: str, params: Dict = None) -> Any:
        """Send a JSON-RPC request and return the response."""
        return self._send_request_sync(method, params)
    
    def send_notification(self, method: str, params: Dict = None) -> None:
        """Send a JSON-RPC notification."""
        self._send_notification(method, params)
