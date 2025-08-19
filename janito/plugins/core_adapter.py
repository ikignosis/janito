"""
Core plugin adapter for legacy plugin system.

This module provides proper Plugin class implementations for core plugins
that use the function-based approach instead of class-based.
"""

from janito.plugins.base import Plugin, PluginMetadata
from typing import List, Type
from janito.tools.tool_base import ToolBase
from janito.tools.function_adapter import create_function_tool


class CorePluginAdapter(Plugin):
    """Adapter for core plugins using function-based tools."""
    
    def __init__(self, plugin_name: str, description: str, tools_module):
        super().__init__()
        self._plugin_name = plugin_name
        self._description = description
        self._tools_module = tools_module
        self._tool_classes = []
        
        # Set the metadata attribute that Plugin expects
        self.metadata = self.get_metadata()
        
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self._plugin_name,
            version="1.0.0",
            description=self._description,
            author="Janito",
            license="MIT",
        )
    
    def get_tools(self) -> List[Type[ToolBase]]:
        return self._tool_classes
    
    def initialize(self):
        """Initialize the plugin by creating tool classes."""
        # Get tools from the module
        tools = getattr(self._tools_module, "__plugin_tools__", [])
        
        self._tool_classes = []
        for tool_func in tools:
            if callable(tool_func):
                tool_class = create_function_tool(tool_func)
                self._tool_classes.append(tool_class)


def create_core_plugin(plugin_name: str, description: str, tools_module) -> CorePluginAdapter:
    """Create a core plugin adapter."""
    return CorePluginAdapter(plugin_name, description, tools_module)