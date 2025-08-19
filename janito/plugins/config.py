"""
Configuration management for plugins using user directory.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


def get_user_config_dir() -> Path:
    """Get the user configuration directory."""
    return Path.home() / ".janito"


def get_plugins_config_path() -> Path:
    """Get the path to the plugins configuration file."""
    return get_user_config_dir() / "plugins.json"


def load_plugins_config() -> Dict[str, Any]:
    """
    Load plugins configuration from user directory.

    Returns:
        Dict containing plugins configuration
    """
    config_path = get_plugins_config_path()

    if not config_path.exists():
        # Create default config if it doesn't exist
        default_config = {
            "plugins": {
                "paths": [str(Path.home() / ".janito" / "plugins"), "./plugins"],
                "load": {},
            }
        }

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save default config
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        return default_config

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load plugins config from {config_path}: {e}")
        return {"plugins": {"paths": [], "load": {}}}


def save_plugins_config(config: Dict[str, Any]) -> bool:
    """
    Save plugins configuration to user directory.

    Args:
        config: Configuration dict to save

    Returns:
        True if saved successfully
    """
    config_path = get_plugins_config_path()

    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error: Failed to save plugins config to {config_path}: {e}")
        return False


def get_user_plugins_dir() -> Path:
    """Get the user plugins directory."""
    plugins_dir = get_user_config_dir() / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir
