"""
Fixed auto-loader for core plugins.

This module provides a working implementation to load core plugins
without the complex discovery mechanism.
"""

import os
from pathlib import Path
from typing import List
from janito.plugins.manager import PluginManager
from janito.plugin_system.core_loader_fixed import load_core_plugin, get_core_plugins

# List of core plugins that should be enabled by default
CORE_PLUGINS = [
    "core.filemanager",
    "core.codeanalyzer",
    "core.system",
    "core.imagedisplay",
    "dev.pythondev",
    "dev.visualization",
    "ui.userinterface",
    "web.webtools",
]


def load_core_plugins(pm: PluginManager = None) -> List[str]:
    """
    Load all core plugins.

    Args:
        pm: PluginManager instance. If None, creates a new one.

    Returns:
        List of successfully loaded plugin names
    """
    if pm is None:
        pm = PluginManager()

    loaded = []

    # Load core plugins
    for plugin_name in CORE_PLUGINS:
        try:
            plugin = load_core_plugin(plugin_name)
            if plugin:
                # Manually register the plugin
                pm.plugins[plugin_name] = plugin
                loaded.append(plugin_name)
        except Exception as e:
            print(f"Warning: Failed to load core plugin {plugin_name}: {e}")

    return loaded


def get_loaded_core_plugins() -> List[str]:
    """
    Get list of currently loaded core plugins.

    Returns:
        List of loaded core plugin names
    """
    pm = PluginManager()
    loaded = pm.list_plugins()
    return [p for p in loaded if p in CORE_PLUGINS]


def is_core_plugin(plugin_name: str) -> bool:
    """
    Check if a plugin is a core plugin.

    Args:
        plugin_name: Name of the plugin to check

    Returns:
        True if it's a core plugin
    """
    return plugin_name in CORE_PLUGINS


# Auto-load core plugins when module is imported
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager with core plugins loaded."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        load_core_plugins(_plugin_manager)
    return _plugin_manager
