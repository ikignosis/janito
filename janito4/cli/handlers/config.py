"""Configuration-related CLI handlers."""

import sys
import json

try:
    from ...general_config import (
        get_config_path,
        get_config_from_cli,
        set_config_from_cli,
        unset_config_value
    )
except ImportError:
    from janito4.general_config import (
        get_config_path,
        get_config_from_cli,
        set_config_from_cli,
        unset_config_value
    )


def handle_get_config(key: str) -> int:
    """Handle --get command.
    
    Args:
        key: Configuration key to retrieve
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        value = get_config_from_cli(key)
        if value is not None:
            print(value)
            return 0
        else:
            print(f"Key '{key}' not found in config", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print(f"Config file not found: {get_config_path()}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}", file=sys.stderr)
        return 1


def handle_set_config(value_str: str) -> int:
    """Handle --set command.
    
    Args:
        value_str: Key=value string to set
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        key, value = set_config_from_cli(value_str)
        print(f"[OK] Set {key}={value} in {get_config_path()}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Usage: janito4 --set model=gpt-4", file=sys.stderr)
        return 1


def handle_unset_config(key: str) -> int:
    """Handle --unset command.
    
    Args:
        key: Configuration key to remove
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if unset_config_value(key):
        print(f"[OK] Removed '{key}' from {get_config_path()}")
        return 0
    else:
        print(f"Key '{key}' not found in config", file=sys.stderr)
        return 1
