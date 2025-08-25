"""
Plugin manager for loading and managing plugins.
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from janito.plugin_system.base import Plugin, PluginMetadata
from .discovery import discover_plugins
from .config import load_plugins_config, get_user_plugins_dir
from .builtin import BuiltinPluginRegistry, load_builtin_plugin
from janito.tools.adapters.local import LocalToolsAdapter

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin loading, registration, and lifecycle.
    """

    def __init__(self, tools_adapter: Optional[LocalToolsAdapter] = None):
        self.tools_adapter = tools_adapter or LocalToolsAdapter()
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_paths: List[Path] = []

    def add_plugin_path(self, path: str) -> None:
        """Add a directory to search for plugins."""
        plugin_path = Path(path)
        if plugin_path.exists() and plugin_path.is_dir():
            self.plugin_paths.append(plugin_path)
            if str(plugin_path) not in sys.path:
                sys.path.insert(0, str(plugin_path))

    def load_plugin(
        self, plugin_name: str, config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Load a plugin by name.

        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin

        Returns:
            True if plugin loaded successfully
        """
        try:
            if plugin_name in self.plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return True

            plugin = discover_plugins(plugin_name, self.plugin_paths)
            if not plugin:
                logger.error(f"Plugin {plugin_name} not found")
                return False

            # Store config
            if config:
                self.plugin_configs[plugin_name] = config

            # Validate config if provided
            if config and hasattr(plugin, "validate_config"):
                if not plugin.validate_config(config):
                    logger.error(f"Invalid configuration for plugin {plugin_name}")
                    return False

            # Initialize plugin
            plugin.initialize()

            # Register tools
            tools = plugin.get_tools()
            for tool_class in tools:
                self.tools_adapter.register_tool(tool_class)

            # Store plugin
            self.plugins[plugin_name] = plugin

            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if plugin unloaded successfully
        """
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return False

            plugin = self.plugins[plugin_name]

            # Unregister tools
            tools = plugin.get_tools()
            for tool_class in tools:
                tool_name = getattr(tool_class(), "tool_name", None)
                if tool_name:
                    self.tools_adapter.unregister_tool(tool_name)

            # Cleanup plugin
            plugin.cleanup()

            # Remove from registry
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]

            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    def list_plugins(self) -> List[str]:
        """Return list of loaded plugin names."""
        return list(self.plugins.keys())

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a loaded plugin."""
        plugin = self.plugins.get(plugin_name)
        return plugin.metadata if plugin else None

    def load_plugins_from_config(self, config: Dict[str, Any]) -> None:
        """
        Load plugins from configuration.

        Args:
            config: Configuration dict with plugin settings
        """
        plugins_config = config.get("plugins", {})

        # Add plugin paths
        for path in plugins_config.get("paths", []):
            self.add_plugin_path(path)

        # Load plugins
        for plugin_name, plugin_config in plugins_config.get("load", {}).items():
            if isinstance(plugin_config, bool):
                if plugin_config:
                    self.load_plugin(plugin_name)
            else:
                self.load_plugin(plugin_name, plugin_config)

    def load_plugins_from_user_config(self) -> None:
        """
        Load plugins from user configuration directory.
        Uses ~/.janito/plugins.json instead of janito.json
        """
        config = load_plugins_config()
        self.load_plugins_from_config(config)

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            True if plugin reloaded successfully
        """
        config = self.plugin_configs.get(plugin_name)
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name, config)

    def get_loaded_plugins_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all loaded plugins."""
        info = {}
        for name, plugin in self.plugins.items():
            info[name] = {
                "metadata": plugin.metadata,
                "tools": [tool.__name__ for tool in plugin.get_tools()],
                "commands": list(plugin.get_commands().keys()),
                "config": self.plugin_configs.get(name, {}),
                "builtin": BuiltinPluginRegistry.is_builtin(name),
                "resources": [
                    {
                        "name": resource.name,
                        "type": resource.type,
                        "description": resource.description,
                        "schema": resource.schema,
                    }
                    for resource in plugin.get_resources()
                ],
            }
        return info

    def get_plugin_resources(self, plugin_name: str) -> List[Dict[str, Any]]:
        """
        Get resources provided by a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            List of resource dictionaries
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return []

        return [
            {
                "name": resource.name,
                "type": resource.type,
                "description": resource.description,
                "schema": resource.schema,
            }
            for resource in plugin.get_resources()
        ]

    def list_all_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all resources from all loaded plugins.

        Returns:
            Dict mapping plugin names to their resources
        """
        all_resources = {}
        for plugin_name in self.plugins:
            all_resources[plugin_name] = self.get_plugin_resources(plugin_name)
        return all_resources
