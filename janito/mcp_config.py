"""
MCP services configuration module for managing ~/.janito/mcp_services.json.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .config_dir import get_config_dir

# Configure logger for this module
logger = logging.getLogger(__name__)

# Default MCP services configuration path. Retained for backward compatibility;
# prefer :func:`get_mcp_config_path` which honors the -c/--config-dir override.
MCP_CONFIG_PATH = get_config_dir() / "mcp_services.json"


def get_mcp_config_path() -> Path:
    """Get the path to the MCP services config file.

    Returns:
        Path: Path to <config-dir>/mcp_services.json (defaults to ~/.janito/mcp_services.json)
    """
    return get_config_dir() / "mcp_services.json"


def load_mcp_config() -> dict[str, Any]:
    """Load MCP services configuration.

    Returns:
        Dict containing the config, or {"services": {}} if file doesn't exist or is invalid
    """
    mcp_config_path = get_mcp_config_path()
    try:
        with open(mcp_config_path, "r") as f:
            config = json.load(f)
            logger.debug(
                f"Loaded MCP config from {mcp_config_path}: {len(config.get('services', {}))} services"
            )
            return config
    except FileNotFoundError:
        logger.debug(f"MCP config file not found: {mcp_config_path}")
        return {"services": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in MCP config file: {e}")
        return {"services": {}}


def save_mcp_config(config: dict[str, Any]) -> None:
    """Save MCP services configuration.

    Args:
        config: Dictionary to save to mcp_services.json

    Raises:
        IOError: If unable to write to the config file
    """
    mcp_config_path = get_mcp_config_path()
    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mcp_config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.debug(f"Saved MCP config to {mcp_config_path}")


def get_service(name: str) -> dict[str, Any] | None:
    """Get a specific MCP service by name.

    Args:
        name: The service name to retrieve

    Returns:
        The service config dict, or None if not found
    """
    config = load_mcp_config()
    return config.get("services", {}).get(name)


def add_service(name: str, service_config: dict[str, Any]) -> None:
    """Add or update an MCP service.

    Args:
        name: The service name
        service_config: The service configuration dict
    """
    config = load_mcp_config()
    if "services" not in config:
        config["services"] = {}
    config["services"][name] = service_config
    save_mcp_config(config)


def remove_service(name: str) -> bool:
    """Remove an MCP service by name.

    Args:
        name: The service name to remove

    Returns:
        bool: True if the service was removed, False if it didn't exist
    """
    config = load_mcp_config()
    services = config.get("services", {})

    if name in services:
        del services[name]
        config["services"] = services
        save_mcp_config(config)
        logger.info(f"Removed MCP service: {name}")
        return True

    logger.debug(f"MCP service not found for removal: {name}")
    return False


def list_services() -> dict[str, dict[str, Any]]:
    """List all configured MCP services.

    Returns:
        Dict mapping service names to their configurations
    """
    config = load_mcp_config()
    return config.get("services", {})
