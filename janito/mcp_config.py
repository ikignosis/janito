"""
MCP services configuration module for managing ~/.janito/mcp_services.json.
"""

import logging
from pathlib import Path
from typing import Any

from .config_dir import get_config_dir
from .json_store import McpConfigStore

# Configure logger for this module
logger = logging.getLogger(__name__)

# Module-level singleton store backing every function below.
_store = McpConfigStore()

# Default MCP services configuration path. Retained for backward compatibility;
# prefer :func:`get_mcp_config_path` which honors the -c/--config-dir override.
MCP_CONFIG_PATH = get_config_dir() / "mcp_services.json"


def get_mcp_config_path() -> Path:
    """Get the path to the MCP services config file.

    Returns:
        Path: Path to <config-dir>/mcp_services.json (defaults to ~/.janito/mcp_services.json)
    """
    return _store.file_path()


def load_mcp_config() -> dict[str, Any]:
    """Load MCP services configuration.

    Returns:
        Dict containing the config, or {"services": {}} if file doesn't exist or is invalid
    """
    return _store.load()


def save_mcp_config(config: dict[str, Any]) -> None:
    """Save MCP services configuration.

    Args:
        config: Dictionary to save to mcp_services.json

    Raises:
        IOError: If unable to write to the config file
    """
    _store.save(config)


def get_service(name: str) -> dict[str, Any] | None:
    """Get a specific MCP service by name.

    Args:
        name: The service name to retrieve

    Returns:
        The service config dict, or None if not found
    """
    return _store.get_service(name)


def add_service(name: str, service_config: dict[str, Any]) -> None:
    """Add or update an MCP service.

    Args:
        name: The service name
        service_config: The service configuration dict
    """
    _store.add_service(name, service_config)


def remove_service(name: str) -> bool:
    """Remove an MCP service by name.

    Args:
        name: The service name to remove

    Returns:
        bool: True if the service was removed, False if it didn't exist
    """
    return _store.remove_service(name)


def list_services() -> dict[str, dict[str, Any]]:
    """List all configured MCP services.

    Returns:
        Dict mapping service names to their configurations
    """
    return _store.list_services()
