"""
MCP Manager - manages multiple MCP server connections and tool routing.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .mcp_client.base import MCPTransport
from .mcp_client.factory import create_transport
from .mcp_config import list_services, get_service
from .tooling.reporter import (
    report_start,
    report_progress,
    report_result,
    report_error,
)

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manages multiple MCP server connections and provides unified tool access.
    """
    
    def __init__(self):
        """Initialize the MCP manager."""
        self._clients: Dict[str, MCPTransport] = {}
        self._tools_cache: Optional[List[Dict]] = None
        self._cache_valid = False    
    @property
    def connected_services(self) -> List[str]:
        """Get list of connected service names."""
        return list(self._clients.keys())
    
    def load_services(self, service_names: List[str] = None) -> None:
        """
        Load and connect to MCP services.
        
        Args:
            service_names: Optional list of specific service names to load.
                         If None, loads all configured services.
        """
        # Get services to load
        if service_names:
            services = {name: get_service(name) for name in service_names if get_service(name)}
        else:
            services = list_services()
        
        # Load each service
        for name, config in services.items():
            if name in self._clients:
                logger.debug(f"Service '{name}' already loaded")
                continue
            
            try:
                transport = create_transport(config)
                if transport.connect():
                    self._clients[name] = transport
                    logger.info(f"Loaded MCP service: {name}")
                else:
                    logger.warning(f"Failed to connect to MCP service: {name}")
            except Exception as e:
                logger.error(f"Error loading MCP service '{name}': {e}")
        
        # Invalidate cache when services change
        self._cache_valid = False
    
    def unload_service(self, name: str) -> None:
        """
        Unload and disconnect a specific service.
        
        Args:
            name: The service name to unload
        """
        if name in self._clients:
            try:
                self._clients[name].disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting service '{name}': {e}")
            finally:
                del self._clients[name]
                self._cache_valid = False
                logger.info(f"Unloaded MCP service: {name}")
    
    def unload_all(self) -> None:
        """Unload all MCP services."""
        service_names = list(self._clients.keys())
        for name in service_names:
            self.unload_service(name)
    
    def get_all_tools(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all tools from all connected MCP servers.
        
        Args:
            force_refresh: If True, bypass cache and refresh tools
            
        Returns:
            List of OpenAI-formatted tool schemas
        """
        if self._cache_valid and not force_refresh:
            return self._tools_cache or []
        
        all_tools = []
        
        for service_name, client in self._clients.items():
            try:
                if not client.is_connected:
                    # Try to reconnect
                    if client.connect():
                        continue
                    else:
                        logger.warning(f"Service '{service_name}' is not connected")
                        continue
                
                # Get tools from this service
                mcp_tools = client.list_tools()
                
                # Convert MCP tools to OpenAI format with service prefix
                for tool in mcp_tools:
                    openai_tool = self._convert_tool_to_openai(service_name, tool)
                    all_tools.append(openai_tool)
                    
            except Exception as e:
                logger.error(f"Error getting tools from service '{service_name}': {e}")
        
        # Cache the results
        self._tools_cache = all_tools
        self._cache_valid = True
        
        logger.info(f"Retrieved {len(all_tools)} tools from {len(self._clients)} MCP services")
        return all_tools
    
    def get_all_prompts(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all prompts from all connected MCP servers.
        
        Args:
            force_refresh: If True, bypass cache and refresh prompts
            
        Returns:
            List of prompts with service prefix
        """
        all_prompts = []
        
        for service_name, client in self._clients.items():
            try:
                if not client.is_connected:
                    continue
                
                # Get prompts from this service
                mcp_prompts = client.list_prompts()
                
                # Add service prefix to each prompt
                for prompt in mcp_prompts:
                    prefixed_prompt = {
                        "name": f"{service_name}_{prompt.get('name', '')}",
                        "description": prompt.get("description", ""),
                        "arguments": prompt.get("arguments", []),
                        "service": service_name,
                        "original_name": prompt.get("name", "")
                    }
                    all_prompts.append(prefixed_prompt)
                    
            except Exception as e:
                logger.error(f"Error getting prompts from service '{service_name}': {e}")
        
        logger.info(f"Retrieved {len(all_prompts)} prompts from {len(self._clients)} MCP services")
        return all_prompts
    
    def get_prompt(self, prefixed_name: str, arguments: Dict = None) -> Any:
        """
        Get a prompt from an MCP server.
        
        Args:
            prefixed_name: The prompt name with service prefix (e.g., "learn_code_example")
            arguments: Optional arguments for the prompt
            
        Returns:
            The prompt content (messages)
        """
        # Find the service for this prompt
        service_name = self.get_service_for_tool(prefixed_name)
        if not service_name:
            raise ValueError(f"Prompt not found: {prefixed_name}")
        
        # Get the original prompt name
        prompt_name = prefixed_name[len(service_name) + 1:]
        
        # Find the client
        client = self._clients.get(service_name)
        if not client:
            raise ValueError(f"Service '{service_name}' is not connected")
        
        logger.info(f"Getting prompt: {service_name}.{prompt_name}")
        result = client.get_prompt(prompt_name, arguments)
        
        return result
    
    def _convert_tool_to_openai(self, service_name: str, mcp_tool: Dict) -> Dict:
        """
        Convert an MCP tool schema to OpenAI function format.
        
        Args:
            service_name: The name of the MCP service
            mcp_tool: The MCP tool schema
            
        Returns:
            OpenAI-formatted tool schema
        """
        tool_name = mcp_tool.get("name", "")
        description = mcp_tool.get("description", "")
        input_schema = mcp_tool.get("inputSchema", {})
        
        # Create prefixed name
        prefixed_name = f"{service_name}_{tool_name}"
        
        return {
            "type": "function",
            "function": {
                "name": prefixed_name,
                "description": f"[{service_name}] {description}",
                "parameters": self._convert_input_schema(input_schema)
            }
        }
    
    def _convert_input_schema(self, schema: Dict) -> Dict:
        """
        Convert MCP input schema to OpenAI parameters format.
        
        Args:
            schema: MCP inputSchema
            
        Returns:
            OpenAI-formatted parameters schema
        """
        # Handle both dict and string formats
        if isinstance(schema, str):
            schema = json.loads(schema) if schema else {}
        
        # MCP uses a superset of JSON Schema, OpenAI uses a subset
        # Extract relevant parts
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def call_tool(self, prefixed_name: str, arguments: Dict) -> Any:
        """
        Call an MCP tool by its prefixed name.
        
        Args:
            prefixed_name: The tool name with service prefix (e.g., "myserver_read_file")
            arguments: The tool arguments
            
        Returns:
            The tool execution result
            
        Raises:
            ValueError: If the tool is not found or format is invalid
        """
        # Parse the prefixed name
        if "_" not in prefixed_name:
            raise ValueError(f"Invalid MCP tool name format: {prefixed_name}")
        
        # Report start of MCP tool call
        report_start(f"MCP tool: {prefixed_name}", end="")
        
        # Find the service (last underscore-separated part is the tool name)
        # We need to find the service name by checking which clients have this tool
        for service_name, client in self._clients.items():
            tool_name = prefixed_name[len(service_name) + 1:]
            
            # Check if this client has this tool
            try:
                if not client.is_connected:
                    continue
                    
                tools = client.list_tools()
                tool_names = [t.get("name") for t in tools]
                
                if tool_name in tool_names:
                    # Show which service we're calling
                    report_progress(f" [{service_name}]", end="")
                    
                    try:
                        result = client.call_tool(tool_name, arguments)
                        processed_result = self._process_tool_result(result)
                        
                        # Report success with result summary
                        result_summary = self._get_result_summary(processed_result)
                        report_result(result_summary)
                        
                        return processed_result
                        
                    except Exception as e:
                        report_error(f" MCP tool error: {str(e)}")
                        raise
                        
            except Exception as e:
                logger.error(f"Error calling tool '{prefixed_name}': {e}")
                raise
        
        report_error(f"MCP tool not found: {prefixed_name}")
        raise ValueError(f"Tool not found: {prefixed_name}")
    
    def _process_tool_result(self, result: Any) -> Any:
        """
        Process a tool result from MCP server.
        
        Args:
            result: The raw tool result
            
        Returns:
            Processed result suitable for returning to the AI
        """
        if isinstance(result, dict):
            # Handle structured results
            content = result.get("content", [])
            
            if isinstance(content, list):
                # MCP returns content as a list of content blocks
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        text_parts.append(f"[Image: {block.get('data', 'N/A')}]")
                
                if text_parts:
                    return "\n".join(text_parts)
            
            # Fallback to returning the result as-is
            if content:
                return content
        
        # Handle direct string or other results
        return result
    
    def _get_result_summary(self, result: Any) -> str:
        """
        Generate a human-readable summary of the tool result.
        
        Args:
            result: The processed tool result
            
        Returns:
            A summary string describing the result
        """
        if result is None:
            return "completed (no output)"
        
        if isinstance(result, str):
            # Truncate long results
            if len(result) > 100:
                lines = result.split("\n")
                if len(lines) > 5:
                    return f"returned {len(lines)} lines ({len(result)} chars)"
                return f"returned {len(result)} chars"
            return f"returned: {result[:100]}"
        
        if isinstance(result, list):
            return f"returned {len(result)} items"
        
        if isinstance(result, dict):
            keys = list(result.keys())
            if len(keys) <= 3:
                return f"returned keys: {', '.join(keys)}"
            return f"returned {len(keys)} keys"
        
        return f"returned {type(result).__name__}"
    
    def get_service_for_tool(self, prefixed_name: str) -> Optional[str]:
        """
        Find which service provides a given tool.
        
        Args:
            prefixed_name: The prefixed tool name
            
        Returns:
            The service name, or None if not found
        """
        for service_name in self._clients.keys():
            if prefixed_name.startswith(f"{service_name}_"):
                return service_name
        return None
    
    def shutdown(self) -> None:
        """Shutdown all connections and cleanup."""
        self.unload_all()
        self._tools_cache = None
        self._cache_valid = False
        logger.info("MCP Manager shutdown complete")


# Global instance for easy access
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


def shutdown_mcp_manager() -> None:
    """Shutdown the global MCP manager."""
    global _mcp_manager
    if _mcp_manager:
        _mcp_manager.shutdown()
        _mcp_manager = None
