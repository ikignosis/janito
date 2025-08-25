"""
Plugin System Core Package

This package provides the foundational plugin system architecture.
It should not depend on any specific plugin implementations.
"""

from .base import Plugin, PluginMetadata, PluginResource

__all__ = ["Plugin", "PluginMetadata", "PluginResource"]
