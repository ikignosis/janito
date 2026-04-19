"""
General configuration module for managing ~/.janito/config.json.

This module provides a centralized interface for all config.json-related operations.
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logger for this module
logger = logging.getLogger(__name__)


# Config file path
CONFIG_PATH = Path.home() / ".janito" / "config.json"


def get_config_path() -> Path:
    """Get the path to the config.json file.
    
    Returns:
        Path: Path to ~/.janito/config.json
    """
    return CONFIG_PATH


def load_config() -> Dict[str, Any]:
    """Load the entire config.json file.
    
    Returns:
        Dict containing the config, or empty dict if file doesn't exist or is invalid
    """
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            logger.debug(f"Loaded config from {CONFIG_PATH}: {list(config.keys())}")
            return config
    except FileNotFoundError:
        logger.debug(f"Config file not found: {CONFIG_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save the config dictionary to config.json.
    
    Args:
        config: Dictionary to save to config.json
        
    Raises:
        IOError: If unable to write to the config file
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    logger.debug(f"Saved config to {CONFIG_PATH}")


def get_config_value(key: str) -> Optional[Any]:
    """Get a config value by key.
    
    Args:
        key: The config key to retrieve
        
    Returns:
        The config value, or None if not found or config file doesn't exist
    """
    config = load_config()
    value = config.get(key)
    logger.debug(f"Getting config '{key}': {value if value is None else '(set)'}")
    return value


def set_config_value(key: str, value: Any) -> None:
    """Set a config value.
    
    Args:
        key: The config key to set
        value: The value to set
    """
    logger.debug(f"Setting config '{key}' = {value}")
    config = load_config()
    config[key] = value
    save_config(config)


def unset_config_value(key: str) -> bool:
    """Remove a config value by key.
    
    Args:
        key: The config key to remove
        
    Returns:
        bool: True if the key was removed, False if it didn't exist
    """
    config = load_config()
    if key in config:
        del config[key]
        save_config(config)
        logger.info(f"Removed config key: {key}")
        return True
    logger.debug(f"Config key not found for removal: {key}")
    return False


def load_provider_from_config() -> Optional[str]:
    """Load provider name from ~/.janito/config.json if it exists.
    
    Returns:
        str: Provider name from config, or None if not found
    """
    return get_config_value("provider")


def load_model_from_config() -> Optional[str]:
    """Load model name from ~/.janito/config.json if it exists.
    
    Returns:
        str: Model name from config, or None if not found
    """
    return get_config_value("model")


def load_context_window_size() -> Optional[int]:
    """Load context window size from ~/.janito/config.json if it exists.
    
    This value can be used to limit the context window size for API calls.
    
    Returns:
        int: Context window size from config, or None if not found
    """
    # Support both hyphenated and underscore formats in config
    value = get_config_value("context-window-size")
    if value is not None:
        return int(value)
    value = get_config_value("context_window_size")
    if value is not None:
        return int(value)
    return None


def load_endpoint_from_config() -> Optional[str]:
    """Load custom endpoint URL from ~/.janito/config.json if it exists.
    
    This is used for the 'custom' provider or to override provider base URLs.
    
    Returns:
        str: Endpoint URL from config, or None if not found
    """
    return get_config_value("endpoint")


def get_masked_api_key(api_key: str) -> str:
    """Mask an API key to show only first and last few characters.
    
    Args:
        api_key: The API key to mask
        
    Returns:
        str: Masked API key showing first 6 and last 4 characters
    """
    if not api_key:
        return "(not set)"
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:6]}...{api_key[-4:]}"


def get_active_provider() -> str:
    """Determine the active provider based on config.
    
    Priority:
    1. Provider from config.json
    2. Default provider from auth.json
    3. Fallback to 'openai'
    
    Returns:
        str: The active provider name
    """
    # 1. Check config.json for provider
    config_provider = load_provider_from_config()
    if config_provider:
        logger.debug(f"Active provider from config: {config_provider}")
        return config_provider
    
    # 3. Check auth.json for default provider
    try:
        from .auth_config import get_default_provider
    except ImportError:
        try:
            from auth_config import get_default_provider
        except ImportError:
            logger.debug("No provider config, using fallback: openai")
            return "openai"
    
    default_provider = get_default_provider()
    if default_provider:
        logger.debug(f"Active provider from auth defaults: {default_provider}")
        return default_provider
    
    # 4. Fall back to 'openai'
    logger.debug("No provider found, using fallback: openai")
    return "openai"


def set_config_from_cli(key_value: str) -> tuple[str, str]:
    """Set a config key-value pair from CLI input.
    
    Args:
        key_value: A string in the format "KEY=VALUE"
        
    Returns:
        tuple: (key, value) that was set
        
    Raises:
        ValueError: If the format is invalid
    """
    if '=' not in key_value:
        raise ValueError("--set requires KEY=VALUE format")
    
    key, value = key_value.split('=', 1)
    key = key.strip()
    value = value.strip()
    
    set_config_value(key, value)
    
    return key, value


def get_config_from_cli(key: str) -> Optional[str]:
    """Get a config value from CLI.
    
    Args:
        key: The config key to retrieve
        
    Returns:
        The config value, or None if not found
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file contains invalid JSON
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    value = config.get(key)
    if value is None:
        return None
    
    # Convert non-string values to string for printing
    if not isinstance(value, str):
        return json.dumps(value)
    return value
