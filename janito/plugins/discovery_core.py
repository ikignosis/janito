"""
Core plugin discovery utilities.

This module provides specialized handling for core plugins that use
the function-based approach instead of class-based plugins.
"""

import importlib.util
from pathlib import Path
from typing import Optional
import sys

from .base import Plugin
from .core_adapter import CorePluginAdapter


def _load_core_plugin(package_path: Path, plugin_name: str) -> Optional[Plugin]:
    """
    Load a core plugin from a package directory.

    Args:
        package_path: Path to the __init__.py file
        plugin_name: Full plugin name (e.g., core.filemanager)

    Returns:
        Plugin instance if loaded successfully
    """
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location(plugin_name, package_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get plugin metadata
        plugin_name_attr = getattr(module, "__plugin_name__", plugin_name)
        description = getattr(
            module, "__plugin_description__", f"Core plugin: {plugin_name}"
        )

        # Create and return the core plugin adapter
        plugin = CorePluginAdapter(plugin_name_attr, description, module)
        plugin.initialize()  # Initialize to set up tools
        return plugin

    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
            f"Failed to load core plugin {plugin_name}: {e}"
        )
        return None
