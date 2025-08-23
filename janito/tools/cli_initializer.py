"""
CLI-specific tool initialization for janito.

This module provides functions to initialize tools specifically for CLI usage,
handling circular imports and ensuring proper registration.
"""

import sys
from pathlib import Path
from typing import List, Optional

# Ensure current directory is in path
sys.path.insert(0, str(Path.cwd()))


def initialize_cli_tools():
    """Initialize tools for CLI usage, avoiding circular imports."""
    try:
        from janito.tools.adapters.local.adapter import LocalToolsAdapter
        from janito.plugin_system.core_loader_fixed import load_core_plugin
        from janito.tools.permissions import set_global_allowed_permissions
        from janito.tools.tool_base import ToolPermissions

        # Create adapter
        adapter = LocalToolsAdapter()

        # Set permissions for CLI
        set_global_allowed_permissions(
            ToolPermissions(read=True, write=True, execute=True)
        )

        # Core plugins to load
        core_plugins = [
            "core.filemanager",
            "core.codeanalyzer",
            "core.system",
            "core.imagedisplay",
            "dev.pythondev",
            "dev.visualization",
        ]

        loaded_count = 0
        for plugin_name in core_plugins:
            plugin = load_core_plugin(plugin_name)
            if plugin:
                tools = plugin.get_tools()
                for tool_class in tools:
                    try:
                        adapter.register_tool(tool_class)
                        loaded_count += 1
                    except ValueError:
                        # Tool already registered, skip
                        pass

        return adapter, loaded_count

    except Exception as e:
        print(f"Error initializing CLI tools: {e}", file=sys.stderr)
        return None, 0


def get_cli_tools_adapter():
    """Get a CLI-initialized tools adapter."""
    adapter, count = initialize_cli_tools()
    if adapter and count > 0:
        return adapter
    return None


def list_cli_tools():
    """List all available CLI tools."""
    adapter = get_cli_tools_adapter()
    if not adapter:
        return []

    return adapter.list_tools()


if __name__ == "__main__":
    adapter, count = initialize_cli_tools()
    if adapter:
        tools = adapter.list_tools()
        print(f"CLI initialized {count} tools")
        print(f"Available tools: {len(tools)}")
        for tool in sorted(tools):
            print(f"  - {tool}")
    else:
        print("Failed to initialize CLI tools")
