#!/usr/bin/env python3
"""
Initialize janito tools for CLI usage.

This script loads all core plugins and registers their tools
with the local tools adapter.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from janito.plugins.core_loader_fixed import load_core_plugin
from janito.tools.adapters.local.adapter import LocalToolsAdapter


def init_janito_tools():
    """Initialize all janito tools for CLI usage."""
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

    loaded = 0
    for plugin_name in core_plugins:
        plugin = load_core_plugin(plugin_name)
        if plugin:
            tools = plugin.get_tools()
            for tool_class in tools:
                adapter.register_tool(tool_class)
                loaded += 1

    return adapter, loaded


if __name__ == "__main__":
    adapter, count = init_janito_tools()
    print(f"Initialized {count} tools")
    print("Available tools:")
    for tool_name in sorted(list(adapter._tools.keys())):
        print(f"  - {tool_name}")
