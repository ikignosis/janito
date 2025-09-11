"""
Builtin plugin system for janito-packaged plugins.

This module provides the infrastructure for plugins that are bundled
with janito and available by default without requiring external installation.
"""

import importlib
from typing import Dict, List, Optional, Type
from janito.plugins.base import Plugin


class BuiltinPluginRegistry:
    """Registry for builtin plugins that come packaged with janito."""

    _plugins: Dict[str, Type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_class: Type[Plugin]) -> None:
        """Register a builtin plugin."""
        cls._plugins[name] = plugin_class

    @classmethod
    def get_plugin_class(cls, name: str) -> Optional[Type[Plugin]]:
        """Get the plugin class for a builtin plugin."""
        return cls._plugins.get(name)

    @classmethod
    def list_builtin_plugins(cls) -> List[str]:
        """List all registered builtin plugins."""
        return list(cls._plugins.keys())

    @classmethod
    def is_builtin(cls, name: str) -> bool:
        """Check if a plugin is builtin."""
        return name in cls._plugins


def register_builtin_plugin(name: str):
    """Decorator to register a plugin as builtin."""

    def decorator(plugin_class: Type[Plugin]) -> Type[Plugin]:
        BuiltinPluginRegistry.register(name, plugin_class)
        return plugin_class

    return decorator


def load_builtin_plugin(name: str) -> Optional[Plugin]:
    """Load a builtin plugin by name."""
    plugin_class = BuiltinPluginRegistry.get_plugin_class(name)
    if plugin_class:
        return plugin_class()
    return None


# Note: External plugin packages can be registered here if needed
# For example, to auto-register plugins from external packages:
# try:
#     from external_package.plugins import SomePlugin
#     BuiltinPluginRegistry.register("some_plugin", SomePlugin)
# except ImportError:
#     # external_package not available, skip registration
#     pass
