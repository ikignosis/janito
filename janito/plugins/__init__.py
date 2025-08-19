"""
Plugin system for janito.

This package provides a flexible plugin system that allows extending
janito's functionality with custom tools, commands, and features.
"""

from .manager import PluginManager
from .base import Plugin, PluginMetadata
from .discovery import discover_plugins

__all__ = [
    "PluginManager",
    "Plugin",
    "PluginMetadata",
    "discover_plugins",
]
