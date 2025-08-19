"""
CLI command to enable/disable plugins by modifying plugins.json configuration.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any
from janito.plugins.config import (
    load_plugins_config,
    save_plugins_config,
    get_plugins_config_path,
)
from janito.plugins.manager import PluginManager


def handle_enable_plugin(args: argparse.Namespace) -> None:
    """Enable a plugin by adding it to plugins.json."""
    config = load_plugins_config()

    if "plugins" not in config:
        config["plugins"] = {}
    if "load" not in config["plugins"]:
        config["plugins"]["load"] = {}

    # Set the plugin to enabled (True)
    config["plugins"]["load"][args.plugin_name] = True

    if save_plugins_config(config):
        print(
            f"Plugin '{args.plugin_name}' has been enabled in {get_plugins_config_path()}"
        )
        print(
            "Note: You may need to reload the plugin in the current session with 'plugin reload'"
        )
    else:
        print(f"Error: Failed to enable plugin '{args.plugin_name}'")


def handle_disable_plugin(args: argparse.Namespace) -> None:
    """Disable a plugin by removing it from plugins.json or setting it to False."""
    config = load_plugins_config()

    if (
        "plugins" in config
        and "load" in config["plugins"]
        and args.plugin_name in config["plugins"]["load"]
    ):
        # Remove the plugin entry or set it to False
        if args.remove:
            del config["plugins"]["load"][args.plugin_name]
            action = "removed"
        else:
            config["plugins"]["load"][args.plugin_name] = False
            action = "disabled"

        if save_plugins_config(config):
            print(
                f"Plugin '{args.plugin_name}' has been {action} in {get_plugins_config_path()}"
            )
            print(
                "Note: You may need to unload the plugin in the current session with 'plugin unload'"
            )
        else:
            print(f"Error: Failed to {action} plugin '{args.plugin_name}'")
    else:
        print(
            f"Plugin '{args.plugin_name}' is not currently configured in plugins.json"
        )
        print(
            "It may still be loaded in the current session, but won't be loaded on restart"
        )


def add_enable_plugin_args(parser: argparse.ArgumentParser) -> None:
    """Add enable-plugin arguments to argument parser."""
    parser.add_argument("plugin_name", help="Name of the plugin to enable")


def add_disable_plugin_args(parser: argparse.ArgumentParser) -> None:
    """Add disable-plugin arguments to argument parser."""
    parser.add_argument("plugin_name", help="Name of the plugin to disable")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Completely remove the plugin from config instead of setting to False",
    )
