"""
Authentication configuration management for Janito CLI.

Handles storage and retrieval of API keys in ~/.janito/auth.json

Structure:
{
    "provider": "openai",  # Optional: default provider to use
    "openai": "sk-xxxxx..."
}
"""

import json
import logging
import os
from pathlib import Path

from .config_dir import get_config_dir, get_config_file_paths

# Configure logger for this module
logger = logging.getLogger(__name__)


def get_auth_file_path() -> Path:
    """Get the path to the auth configuration file (the write target)."""
    return get_config_dir() / "auth.json"


def get_auth_file_paths() -> list[Path]:
    """Get all auth.json paths used for resolution, in priority order.

    With ``-l`` / ``--local`` the project-local path (``./.janito/auth.json``)
    comes first, followed by the base path (``~/.janito/auth.json`` or the
    ``-c`` / ``--config-dir`` override). Otherwise only the base path is
    returned.

    Returns:
        List of paths, highest priority first.
    """
    return get_config_file_paths("auth.json")


def ensure_auth_directory() -> Path:
    """Ensure the ~/.janito directory exists."""
    auth_file = get_auth_file_path()
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    return auth_file.parent


def load_auth_config() -> dict[str, str]:
    """Load the authentication configuration from file.

    With ``-l`` / ``--local`` the project-local auth.json (``./.janito``) is
    merged over the base one (``~/.janito`` or the ``-c`` override) so local
    entries take precedence; otherwise only the base file is read.

    Returns:
        Dict of provider -> API key (plus the optional ``provider`` default).
    """
    paths = get_auth_file_paths()

    if not any(path.exists() for path in paths):
        logger.debug("Auth config file not found")
        return {}

    merged: dict[str, str] = {}
    # Iterate base -> local so that local entries override global ones.
    for auth_file in reversed(paths):
        if not auth_file.exists():
            continue
        with open(auth_file, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Loaded auth config from {auth_file}")
        merged.update(json.loads(content))
    return merged


def save_auth_config(config: dict[str, str]) -> bool:
    """Save the authentication configuration to file."""
    try:
        ensure_auth_directory()
        auth_file = get_auth_file_path()

        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Set restrictive permissions (read/write for owner only)
        os.chmod(auth_file, 0o600)
        logger.debug(f"Saved auth config to {auth_file}")
        return True
    except OSError as e:
        logger.error(f"Failed to save auth config: {e}")
        return False


def set_api_key(provider: str, api_key: str) -> bool:
    """
    Set an API key for a specific provider.

    Args:
        provider: The provider name (e.g., 'openai')
        api_key: The actual API key value

    Returns:
        True if successful, False otherwise
    """
    logger.debug(f"Setting API key for provider: {provider}")
    config = load_auth_config()
    config[provider] = api_key
    result = save_auth_config(config)
    if result:
        logger.info(f"API key saved for provider: {provider}")
    return result


def get_api_key(provider: str) -> str | None:
    """
    Get an API key for a specific provider.

    Args:
        provider: The provider name

    Returns:
        The API key if found, None otherwise
    """
    config = load_auth_config()
    api_key = config.get(provider)
    if api_key:
        logger.debug(f"API key found for provider: {provider}")
    else:
        logger.debug(f"No API key found for provider: {provider}")
    return api_key


def list_providers() -> list:
    """
    List all configured providers (API keys).

    Note: This excludes the 'provider' key which is metadata for the default provider.

    Returns:
        List of provider names
    """
    config = load_auth_config()
    return [key for key in config.keys() if key != "provider"]


def delete_api_key(provider: str) -> bool:
    """
    Delete an API key for a specific provider.

    Args:
        provider: The provider name

    Returns:
        True if deleted, False if not found
    """
    config = load_auth_config()

    if provider in config:
        del config[provider]
        return save_auth_config(config)

    return False


def set_default_provider(provider: str) -> bool:
    """
    Set the default provider to use.

    Args:
        provider: The provider name (e.g., 'openai')

    Returns:
        True if successful, False otherwise
    """
    config = load_auth_config()
    config["provider"] = provider
    return save_auth_config(config)


def get_default_provider() -> str | None:
    """
    Get the default provider from configuration.

    Returns:
        The default provider name if set, None otherwise
    """
    config = load_auth_config()
    return config.get("provider")


def get_default_provider_api_key() -> str | None:
    """
    Get the API key for the default provider.

    This function reads the 'provider' key from the config to determine
    which provider to use, then retrieves the corresponding API key.

    Returns:
        The API key for the default provider if found, None otherwise
    """
    provider = get_default_provider()
    if provider:
        return get_api_key(provider)
    return None
