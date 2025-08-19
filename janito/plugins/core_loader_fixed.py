"""
Fixed core plugin loader.

This module provides a working implementation to load core plugins
by directly using the Plugin base class properly.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Type

from janito.plugins.base import Plugin, PluginMetadata
from janito.tools.function_adapter import create_function_tool
from janito.tools.tool_base import ToolBase


class CorePlugin(Plugin):
    """Working core plugin implementation."""
    
    def __init__(self, name: str, description: str, tools: list):
        self._plugin_name = name
        self._description = description
        self._tools = tools
        self._tool_classes = []
        super().__init__()  # Call super after setting attributes
        
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
        """Initialize by creating tool classes."""
        self._tool_classes = []
        for tool_func in self._tools:
            if callable(tool_func):
                tool_class = create_function_tool(tool_func)
                self._tool_classes.append(tool_class)


def load_core_plugin(plugin_name: str) -> Optional[Plugin]:
    """
    Load a core plugin by name.
    
    Args:
        plugin_name: Name of the plugin (e.g., 'core.filemanager')
        
    Returns:
        Plugin instance if loaded successfully
    """
    try:
        # Parse plugin name
        if "." not in plugin_name:
            return None
            
        parts = plugin_name.split(".")
        if len(parts) != 2:
            return None
            
        package_name, submodule_name = parts
        
        # Handle imagedisplay specially
        if plugin_name == "core.imagedisplay":
            # Import the actual plugin class
            try:
                from plugins.core.imagedisplay.plugin import ImageDisplayPlugin
                return ImageDisplayPlugin()
            except ImportError:
                # If import fails, return None - don't return True
                return None
        
        # Build path to plugin
        plugin_path = Path("plugins") / package_name / submodule_name / "__init__.py"
        if not plugin_path.exists():
            return None
            
        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        if spec is None or spec.loader is None:
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get plugin info
        name = getattr(module, "__plugin_name__", plugin_name)
        description = getattr(module, "__plugin_description__", f"Core plugin: {plugin_name}")
        tools = getattr(module, "__plugin_tools__", [])
        
        if not tools:
            return None
            
        # Create plugin
        plugin = CorePlugin(name, description, tools)
        plugin.initialize()
        return plugin
        
    except Exception as e:
        print(f"Error loading core plugin {plugin_name}: {e}")
        return None


def get_core_plugins() -> list:
    """Get list of all available core plugins."""
    core_plugins = [
        "core.filemanager",
        "core.codeanalyzer",
        "core.system",
        "core.imagedisplay",
        "dev.pythondev",
        "dev.visualization",
        "ui.userinterface",
        "web.webtools",
    ]
    
    # All core plugins are always available
    return core_plugins