"""
MCP services configuration module for managing ~/.janito/mcp_services.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logger for this module
logger = logging.getLogger(__name__)

# MCP services configuration path
MCP_CONFIG_PATH = Path.home() / ".janito" / "mcp_services.json"


def get_mcp_config_path() -> Path:
    """Get the path to the MCP services config file.
    
    Returns:
        Path: Path to ~/.janito/mcp_services.json
    """
    return MCP_CONFIG_PATH


def load_mcp_config() -> Dict[str, Any]:
    """Load MCP services configuration.
    
    Returns:
        Dict containing the config, or {"services": {}} if file doesn't exist or is invalid
    """
    try:
        with open(MCP_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            logger.debug(f"Loaded MCP config from {MCP_CONFIG_PATH}: {len(config.get('services', {}))} services")
            return config
    except FileNotFoundError:
        logger.debug(f"MCP config file not found: {MCP_CONFIG_PATH}")
        return {"services": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in MCP config file: {e}")
        return {"services": {}}


def save_mcp_config(config: Dict[str, Any]) -> None:
    """Save MCP services configuration.
    
    Args:
        config: Dictionary to save to mcp_services.json
        
    Raises:
        IOError: If unable to write to the config file
    """
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MCP_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    logger.debug(f"Saved MCP config to {MCP_CONFIG_PATH}")


def get_service(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific MCP service by name.
    
    Args:
        name: The service name to retrieve
        
    Returns:
        The service config dict, or None if not found
    """
    config = load_mcp_config()
    return config.get("services", {}).get(name)


def add_service(name: str, service_config: Dict[str, Any]) -> None:
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


def list_services() -> Dict[str, Dict[str, Any]]:
    """List all configured MCP services.
    
    Returns:
        Dict mapping service names to their configurations
    """
    config = load_mcp_config()
    return config.get("services", {})
