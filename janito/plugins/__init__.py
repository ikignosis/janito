"""
Unified Plugin System for Janito

This package provides a clean, unified plugin architecture for janito.
"""

__version__ = "1.0.0"
__author__ = "Development Assistant"

# Import core components
from .base import Plugin, PluginMetadata, PluginResource
from .manager import PluginManager
from .discovery import discover_plugins, list_available_plugins
from .config import load_plugins_config, save_plugins_config
from .builtin import BuiltinPluginRegistry, load_builtin_plugin

__all__ = [
    "Plugin",
    "PluginMetadata", 
    "PluginResource",
    "PluginManager",
    "discover_plugins",
    "list_available_plugins",
    "load_plugins_config",
    "save_plugins_config",
    "BuiltinPluginRegistry",
    "load_builtin_plugin",
]
