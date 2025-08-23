"""
CLI command to list available and loaded plugins.
"""

import argparse
from typing import List, Dict, Any
from janito.plugins.discovery import list_available_plugins
import os
from janito.plugins.manager import PluginManager
from janito.plugins.builtin import BuiltinPluginRegistry
from janito.plugins.auto_loader_fixed import (
    load_core_plugins,
    get_loaded_core_plugins,
    is_core_plugin,
)
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


def handle_list_plugins(args: argparse.Namespace) -> None:
    """List plugins command handler."""

    if getattr(args, "list_plugins_available", False):
        _list_available_plugins()
    elif getattr(args, "list_resources", False):
        _list_plugin_resources()
    else:
        _list_loaded_plugins()


def _list_available_plugins():
    """List available plugins using rich formatting."""
    console = Console()
    available = list_available_plugins()
    builtin_plugins = BuiltinPluginRegistry.list_builtin_plugins()

    if available or builtin_plugins:
        # Create main table
        table = Table(title="Available Plugins")
        table.add_column("Plugin Name", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")

        # Add builtin plugins
        for plugin in builtin_plugins:
            table.add_row(plugin, "Builtin", "📦")

        # Add external plugins
        other_plugins = [p for p in available if p not in builtin_plugins]
        for plugin in other_plugins:
            table.add_row(plugin, "External", "🔌")

        console.print(table)

        # Show core plugins
        from janito.plugin_system.core_loader_fixed import get_core_plugins

        core_plugins = get_core_plugins()
        core_table = Table(title="Core Plugins (Enabled by Default)")
        core_table.add_column("Plugin Name", style="cyan", no_wrap=True)
        core_table.add_column("Status", style="yellow")

        for plugin in core_plugins:
            core_table.add_row(plugin, "✅ Available")

        console.print(core_table)
    else:
        console.print(
            Panel(
                "No plugins found in search paths\n"
                f"[dim]Search paths:[/dim]\n"
                f"  • {os.getcwd()}/plugins\n"
                f"  • {os.path.expanduser('~')}/.janito/plugins",
                title="No Plugins Found",
                style="yellow",
            )
        )


def _print_builtin_plugins(builtin_plugins):
    """Print builtin plugins."""
    if builtin_plugins:
        print("  Builtin plugins:")
        for plugin in builtin_plugins:
            print(f"    - {plugin} [BUILTIN]")


def _print_external_plugins(available, builtin_plugins):
    """Print external plugins."""
    other_plugins = [p for p in available if p not in builtin_plugins]
    if other_plugins:
        print("  External plugins:")
        for plugin in other_plugins:
            print(f"    - {plugin}")


def _list_plugin_resources():
    """List all resources from loaded plugins using rich formatting."""
    from janito.plugins.auto_loader_fixed import get_plugin_manager

    console = Console()
    manager = get_plugin_manager()
    all_resources = manager.list_all_resources()

    if all_resources:
        for plugin_name, resources in all_resources.items():
            metadata = manager.get_plugin_metadata(plugin_name)
            version = metadata.version if metadata else "unknown"

            # Create panel for each plugin
            panel_content = []

            tools = [r for r in resources if r["type"] == "tool"]
            commands = [r for r in resources if r["type"] == "command"]
            configs = [r for r in resources if r["type"] == "config"]

            if tools:
                panel_content.append("[bold blue]Tools:[/bold blue]")
                for tool in tools:
                    panel_content.append(f"  • {tool['name']}: {tool['description']}")

            if commands:
                panel_content.append("[bold green]Commands:[/bold green]")
                for cmd in commands:
                    panel_content.append(f"  • {cmd['name']}: {cmd['description']}")

            if configs:
                panel_content.append("[bold yellow]Configuration:[/bold yellow]")
                for config in configs:
                    panel_content.append(
                        f"  • {config['name']}: {config['description']}"
                    )

            console.print(
                Panel(
                    "\n".join(panel_content),
                    title=f"{plugin_name} v{version}",
                    style="cyan",
                )
            )
    else:
        console.print(
            Panel(
                "No plugins are currently loaded.",
                title="No Plugin Resources",
                style="yellow",
            )
        )


def _print_resources_by_type(resources):
    """Print resources grouped by type."""
    tools = [r for r in resources if r["type"] == "tool"]
    commands = [r for r in resources if r["type"] == "command"]
    configs = [r for r in resources if r["type"] == "config"]

    if tools:
        print("  Tools:")
        for tool in tools:
            print(f"    - {tool['name']}: {tool['description']}")

    if commands:
        print("  Commands:")
        for cmd in commands:
            print(f"    - {cmd['name']}: {cmd['description']}")

    if configs:
        print("  Configuration:")
        for config in configs:
            print(f"    - {config['name']}: {config['description']}")


def _list_loaded_plugins():
    """List loaded plugins using rich formatting."""
    from janito.plugins.auto_loader_fixed import get_plugin_manager

    console = Console()
    manager = get_plugin_manager()
    loaded = manager.list_plugins()

    if loaded:
        # Create main table
        table = Table(title="Loaded Plugins")
        table.add_column("Plugin Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Description", style="green", max_width=50)
        table.add_column("Type", style="yellow")

        core_plugins = []
        other_plugins = []

        for plugin_name in loaded:
            if is_core_plugin(plugin_name):
                core_plugins.append(plugin_name)
            else:
                other_plugins.append(plugin_name)

        # Add core plugins
        for plugin_name in core_plugins:
            metadata = manager.get_plugin_metadata(plugin_name)
            if metadata:
                table.add_row(
                    metadata.name, metadata.version, metadata.description, "🔵 Core"
                )

        # Add other plugins
        for plugin_name in other_plugins:
            metadata = manager.get_plugin_metadata(plugin_name)
            if metadata:
                table.add_row(
                    metadata.name, metadata.version, metadata.description, "🔶 External"
                )

        console.print(table)
    else:
        console.print(
            Panel(
                "No plugins are currently loaded.",
                title="No Plugins Loaded",
                style="yellow",
            )
        )


def _print_plugin_details(manager, plugin_name):
    """Print details for a loaded plugin."""
    metadata = manager.get_plugin_metadata(plugin_name)
    is_builtin = BuiltinPluginRegistry.is_builtin(plugin_name)
    if metadata:
        builtin_tag = " [BUILTIN]" if is_builtin else ""
        print(f"  - {metadata.name} v{metadata.version}{builtin_tag}")
        print(f"    {metadata.description}")
        if metadata.author:
            print(f"    Author: {metadata.author}")
        print()
