"""
Initialize janito tools for CLI and programmatic usage.

This module provides functions to load core plugins and register their tools
with the local tools adapter.
"""

import sys
from pathlib import Path
from typing import List, Optional

from janito.plugin_system.core_loader_fixed import load_core_plugin
from janito.tools.adapters.local.adapter import LocalToolsAdapter


def initialize_tools(adapter: Optional[LocalToolsAdapter] = None) -> LocalToolsAdapter:
    """
    Initialize all janito tools by loading core plugins and registering tools.

    Args:
        adapter: LocalToolsAdapter instance to register tools with.
                If None, creates a new instance.

    Returns:
        LocalToolsAdapter with all tools registered.
    """
    if adapter is None:
        adapter = LocalToolsAdapter()

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
                adapter.register_tool(tool_class)
                loaded_count += 1

    return adapter


def get_initialized_adapter() -> LocalToolsAdapter:
    """Get a pre-initialized LocalToolsAdapter with all tools registered."""
    return initialize_tools()


def list_available_tools() -> List[str]:
    """Get a list of all available tool names."""
    adapter = get_initialized_adapter()
    return sorted(list(adapter._tools.keys()))


if __name__ == "__main__":
    adapter = initialize_tools()
    tools = sorted(list(adapter._tools.keys()))

    print(f"Initialized {len(tools)} tools")
    print("Available tools:")
    for tool_name in tools:
        print(f"  - {tool_name}")
