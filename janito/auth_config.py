"""
Authentication configuration management for Janito CLI.

Handles storage and retrieval of API keys in ~/.janito/auth.json

Structure:
{
    "openai": "sk-xxxxx..."
}

The default provider is a configuration concern: it is stored under the
``provider`` key in ~/.janito/config.json (see janito.general_config),
never in auth.json.
"""

import logging
from pathlib import Path

from .json_store import AuthConfigStore

# Configure logger for this module
logger = logging.getLogger(__name__)

# Module-level singleton store backing every function below.
_store = AuthConfigStore()


def get_auth_file_path() -> Path:
    """Get the path to the auth configuration file (the write target)."""
    return _store.file_path()


def get_auth_file_paths() -> list[Path]:
    """Get all auth.json paths used for resolution, in priority order.

    With ``-l`` / ``--local`` the project-local path (``./.janito/auth.json``)
    comes first, followed by the base path (``~/.janito/auth.json`` or the
    ``-c`` / ``--config-dir`` override). Otherwise only the base path is
    returned.

    Returns:
        List of paths, highest priority first.
    """
    return _store.file_paths()


def ensure_auth_directory() -> Path:
    """Ensure the ~/.janito directory exists."""
    return _store.ensure_directory()


def load_auth_config() -> dict[str, str]:
    """Load the authentication configuration from file.

    With ``-l`` / ``--local`` the project-local auth.json (``./.janito``) is
    merged over the base one (``~/.janito`` or the ``-c`` override) so local
    entries take precedence; otherwise only the base file is read.

    Returns:
        Dict of provider -> API key.
    """
    return _store.load()


def save_auth_config(config: dict[str, str]) -> bool:
    """Save the authentication configuration to file."""
    return _store.save(config)


def set_api_key(provider: str, api_key: str) -> bool:
    """
    Set an API key for a specific provider.

    The default provider is not touched: it is stored in config.json (the
    ``provider`` key), never in auth.json.

    Args:
        provider: The provider name (e.g., 'openai')
        api_key: The actual API key value

    Returns:
        True if successful, False otherwise
    """
    return _store.set_api_key(provider, api_key)


def get_api_key(provider: str) -> str | None:
    """
    Get an API key for a specific provider.

    Args:
        provider: The provider name

    Returns:
        The API key if found, None otherwise
    """
    return _store.get_api_key(provider)


def list_providers() -> list:
    """
    List all configured providers (API keys).

    Returns:
        List of provider names
    """
    return _store.list_providers()


def delete_api_key(provider: str) -> bool:
    """
    Delete an API key for a specific provider.

    Args:
        provider: The provider name

    Returns:
        True if deleted, False if not found
    """
    return _store.delete_api_key(provider)
