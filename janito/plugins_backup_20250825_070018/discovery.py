"""
Plugin discovery utilities.

Plugins can be provided in several formats:

1. Single Python file: A .py file containing a Plugin class
   Example: plugins/my_plugin.py

2. Python package directory: A directory with __init__.py or plugin.py
   Example: plugins/my_plugin/__init__.py
   Example: plugins/my_plugin/plugin.py

3. Installed Python package: An installed package with a Plugin class
   Example: pip install janito-plugin-example

4. ZIP file: A .zip file containing a Python package structure
   Example: plugins/my_plugin.zip (containing package structure)

The plugin discovery system searches these locations in order:
- Current working directory/plugins/
- ~/.janito/plugins/
- Python installation share/janito/plugins/
- Any additional paths specified via configuration
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Optional, List
import logging

from janito.plugin_system.base import Plugin
from .builtin import load_builtin_plugin, BuiltinPluginRegistry
from janito.plugin_system.core_loader import load_core_plugin

logger = logging.getLogger(__name__)


def discover_plugins(
    plugin_name: str, search_paths: List[Path] = None
) -> Optional[Plugin]:
    """
    Discover and load a plugin by name.

    Supports multiple plugin formats:
    - Single .py files
    - Python package directories
    - Package-based plugins (e.g., core.filemanager)
    - Installed Python packages
    - ZIP files containing packages

    Args:
        plugin_name: Name of the plugin to discover
        search_paths: List of directories to search for plugins

    Returns:
        Plugin instance if found, None otherwise
    """
    if search_paths is None:
        search_paths = []

    # Add default search paths
    default_paths = [
        Path.cwd() / "plugins",
        Path.home() / ".janito" / "plugins",
        Path(sys.prefix) / "share" / "janito" / "plugins",
    ]

    all_paths = search_paths + default_paths

    # Handle package-based plugins (e.g., core.filemanager)
    if "." in plugin_name:
        parts = plugin_name.split(".")
        if len(parts) == 2:
            package_name, submodule_name = parts

            # Handle core plugins with dedicated loader
            if plugin_name.startswith(("core.", "dev.", "ui.", "web.")):
                plugin = load_core_plugin(plugin_name)
                if plugin:
                    return plugin

            for base_path in all_paths:
                package_path = base_path / package_name / submodule_name / "__init__.py"
                if package_path.exists():
                    return _load_plugin_from_file(package_path, plugin_name=plugin_name)

                plugin_path = base_path / package_name / submodule_name / "plugin.py"
                if plugin_path.exists():
                    return _load_plugin_from_file(plugin_path, plugin_name=plugin_name)

    # Try to find plugin in search paths
    for base_path in all_paths:
        plugin_path = base_path / plugin_name
        if plugin_path.exists():
            return _load_plugin_from_directory(plugin_path)

        # Try as Python module
        module_path = base_path / f"{plugin_name}.py"
        if module_path.exists():
            return _load_plugin_from_file(module_path)

    # Check for builtin plugins
    builtin_plugin = load_builtin_plugin(plugin_name)
    if builtin_plugin:
        return builtin_plugin

    # Try importing as installed package
    try:
        return _load_plugin_from_package(plugin_name)
    except ImportError:
        pass

    return None


def _load_plugin_from_directory(plugin_path: Path) -> Optional[Plugin]:
    """Load a plugin from a directory."""
    try:
        # Look for __init__.py or plugin.py
        init_file = plugin_path / "__init__.py"
        plugin_file = plugin_path / "plugin.py"

        if init_file.exists():
            return _load_plugin_from_file(init_file, plugin_name=plugin_path.name)
        elif plugin_file.exists():
            return _load_plugin_from_file(plugin_file, plugin_name=plugin_path.name)

    except Exception as e:
        logger.error(f"Failed to load plugin from directory {plugin_path}: {e}")

    return None


def _load_plugin_from_file(
    file_path: Path, plugin_name: str = None
) -> Optional[Plugin]:
    """Load a plugin from a Python file."""
    try:
        if plugin_name is None:
            plugin_name = file_path.stem

        spec = importlib.util.spec_from_file_location(plugin_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Look for Plugin class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                return attr()

        # Check for package-based plugin with __plugin_name__ metadata
        if hasattr(module, "__plugin_name__"):
            from janito.plugin_system.base import PluginMetadata

            # Create a dynamic plugin class
            class PackagePlugin(Plugin):
                def __init__(self):
                    super().__init__()
                    self._module = module

                def get_metadata(self) -> PluginMetadata:
                    return PluginMetadata(
                        name=getattr(module, "__plugin_name__", plugin_name),
                        version=getattr(module, "__plugin_version__", "1.0.0"),
                        description=getattr(
                            module,
                            "__plugin_description__",
                            f"Package plugin: {plugin_name}",
                        ),
                        author=getattr(module, "__plugin_author__", "Unknown"),
                        license=getattr(module, "__plugin_license__", "MIT"),
                    )

                def get_tools(self):
                    return getattr(module, "__plugin_tools__", [])

                def initialize(self):
                    if hasattr(module, "initialize"):
                        module.initialize()

                def cleanup(self):
                    if hasattr(module, "cleanup"):
                        module.cleanup()

            return PackagePlugin()

    except Exception as e:
        logger.error(f"Failed to load plugin from file {file_path}: {e}")

    return None


def _load_plugin_from_package(package_name: str) -> Optional[Plugin]:
    """Load a plugin from an installed package."""
    try:
        module = importlib.import_module(package_name)

        # Look for Plugin class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                return attr()

    except ImportError as e:
        logger.debug(f"Could not import package {package_name}: {e}")

    return None


def list_available_plugins(search_paths: List[Path] = None) -> List[str]:
    """
    List all available plugins in search paths.

    Scans for plugins in multiple formats:
    - .py files (excluding __init__.py)
    - Directories with __init__.py or plugin.py
    - Package directories with plugin metadata (__plugin_name__)
    - Any valid plugin structure in search paths

    Args:
        search_paths: List of directories to search for plugins

    Returns:
        List of plugin names found
    """
    if search_paths is None:
        search_paths = []

    # Add default search paths
    default_paths = [
        Path.cwd() / "plugins",
        Path.home() / ".janito" / "plugins",
        Path(sys.prefix) / "share" / "janito" / "plugins",
    ]

    all_paths = search_paths + default_paths
    plugins = []

    for base_path in all_paths:
        if not base_path.exists():
            continue

        # Look for directories with __init__.py or plugin.py
        for item in base_path.iterdir():
            if item.is_dir():
                # Check for package-based plugins (subdirectories with __init__.py)
                if (item / "__init__.py").exists():
                    # Check subdirectories for plugin metadata
                    for subitem in item.iterdir():
                        if subitem.is_dir() and (subitem / "__init__.py").exists():
                            try:
                                import importlib.util

                                spec = importlib.util.spec_from_file_location(
                                    f"{item.name}.{subitem.name}",
                                    subitem / "__init__.py",
                                )
                                if spec and spec.loader:
                                    module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(module)

                                    # Check for plugin metadata
                                    if hasattr(module, "__plugin_name__"):
                                        plugins.append(
                                            getattr(module, "__plugin_name__")
                                        )
                            except Exception:
                                pass

                # Also check for plugin.py files
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    plugins.append(item.name)

            elif item.suffix == ".py" and item.stem != "__init__":
                plugins.append(item.stem)

    # Add builtin plugins
    builtin_plugins = BuiltinPluginRegistry.list_builtin_plugins()
    plugins.extend(builtin_plugins)

    return sorted(set(plugins))
