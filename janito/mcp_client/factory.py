"""
Factory for creating MCP transport instances from configuration.
"""

import logging
from typing import Dict, Any

from .base import MCPTransport
from .protocols import MCPError

logger = logging.getLogger(__name__)


def create_transport(config: Dict[str, Any]) -> MCPTransport:
    """
    Factory function to create a transport from configuration.
    
    Args:
        config: Service configuration dict with 'transport' key.
                Must also contain transport-specific settings:
                - stdio: 'command' (required), 'env' (optional)
                - http: 'url' (required), 'headers' (optional)
                
    Returns:
        MCPTransport instance
        
    Raises:
        ValueError: If transport type is unknown or config is invalid
        ImportError: If required dependencies are missing
    """
    # Handle config being a string (direct type specification)
    if isinstance(config, str):
        transport_type = config.lower()
        config = {}
    else:
        transport_type = config.get("transport", "").lower()
    
    # Import transport modules here to avoid circular imports
    if transport_type == "stdio":
        from .stdio import StdioTransport
        
        command = config.get("command", "")
        if not command:
            raise ValueError("stdio transport requires 'command' in config")
        
        return StdioTransport(
            command=command,
            env=config.get("env", {})
        )
    
    elif transport_type == "http":
        from .http import HttpTransport
        
        url = config.get("url", "")
        if not url:
            raise ValueError("http transport requires 'url' in config")
        
        return HttpTransport(
            url=url,
            headers=config.get("headers", {})
        )
    
    else:
        raise ValueError(
            f"Unknown transport type: '{transport_type}'. "
            f"Supported types: 'stdio', 'http'"
        )
