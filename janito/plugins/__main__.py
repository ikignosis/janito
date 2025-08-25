#!/usr/bin/env python3
"""
Plugin system CLI entry point.
"""

import argparse
import sys
from pathlib import Path

from .manager import PluginManager
from .discovery import list_available_plugins
from .core_loader import get_core_plugins


def list_plugins():
    """List all available plugins."""
    print("📋 Available Plugins:")
    print("=" * 50)
    
    # Get available plugins
    available = list_available_plugins()
    
    # Get core plugins
    core_plugins = get_core_plugins()
    
    if available:
        print("\n🔌 Available Plugins:")
        for plugin in sorted(available):
            if plugin in core_plugins:
                print(f"  ✅ {plugin} (core)")
            else:
                print(f"  🔌 {plugin}")
    else:
        print("  No plugins found in search paths")
    
    print(f"\n📊 Total: {len(available)} plugins")


def list_loaded():
    """List currently loaded plugins."""
    print("🔧 Currently Loaded Plugins:")
    print("=" * 50)
    
    pm = PluginManager()
    
    # Load core plugins
    core_plugins = get_core_plugins()
    for plugin in core_plugins:
        pm.load_plugin(plugin)
    
    loaded = pm.list_plugins()
    
    if loaded:
        for plugin in sorted(loaded):
            metadata = pm.get_plugin_metadata(plugin)
            if metadata:
                print(f"  📦 {plugin} v{metadata.version}")
                print(f"     {metadata.description}")
            else:
                print(f"  📦 {plugin}")
    else:
        print("  No plugins currently loaded")
    
    print(f"\n📊 Total: {len(loaded)} plugins loaded")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Janito Plugin System CLI")
    parser.add_argument(
        "--list-plugins", 
        action="store_true", 
        help="List all loaded plugins"
    )
    
    args = parser.parse_args()
    
    if args.list_plugins:
        list_loaded()
    else:
        list_loaded()


if __name__ == "__main__":
    main()