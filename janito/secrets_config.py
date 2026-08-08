"""
Secrets configuration management for Janito CLI.

Handles storage and retrieval of secrets in ~/.janito/secrets.json

Structure:
{
    "key1": "value1",
    "key2": "value2"
}

Secrets are stored separately from auth.json (API keys) to allow for
storing arbitrary secret values like tokens, passwords, or other
credentials that aren't provider-specific API keys.
"""

import json
import logging
import os
from pathlib import Path

from .config_dir import get_config_dir, get_config_file_paths

# Configure logger for this module
logger = logging.getLogger(__name__)


def get_secrets_file_path() -> Path:
    """Get the path to the secrets configuration file (the write target)."""
    return get_config_dir() / "secrets.json"


def get_secrets_file_paths() -> list[Path]:
    """Get all secrets.json paths used for resolution, in priority order.

    With ``-l`` / ``--local`` the project-local path (``./.janito/secrets.json``)
    comes first, followed by the base path (``~/.janito/secrets.json`` or the
    ``-c`` / ``--config-dir`` override). Otherwise only the base path is
    returned.

    Returns:
        List of paths, highest priority first.
    """
    return get_config_file_paths("secrets.json")


def ensure_secrets_directory() -> Path:
    """Ensure the ~/.janito directory exists."""
    secrets_file = get_secrets_file_path()
    secrets_file.parent.mkdir(parents=True, exist_ok=True)
    return secrets_file.parent


def load_secrets_config() -> dict[str, str]:
    """Load the secrets configuration from file.

    With ``-l`` / ``--local`` the project-local secrets.json (``./.janito``)
    is merged over the base one (``~/.janito`` or the ``-c`` override) so local
    entries take precedence; otherwise only the base file is read.

    Returns:
        Dict[str, str]: Dictionary of key-value secrets
    """
    paths = get_secrets_file_paths()

    if not any(path.exists() for path in paths):
        logger.debug("Secrets config file not found")
        return {}

    merged: dict[str, str] = {}
    # Iterate base -> local so that local entries override global ones.
    for secrets_file in reversed(paths):
        if not secrets_file.exists():
            continue
        try:
            with open(secrets_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"Loaded secrets config from {secrets_file}")
            merged.update(json.loads(content))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets config: {e}")
            continue
    return merged


def save_secrets_config(config: dict[str, str]) -> bool:
    """Save the secrets configuration to file.

    Args:
        config: Dictionary of secrets to save

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ensure_secrets_directory()
        secrets_file = get_secrets_file_path()

        with open(secrets_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Set restrictive permissions (read/write for owner only)
        os.chmod(secrets_file, 0o600)
        logger.debug(f"Saved secrets config to {secrets_file}")
        return True
    except OSError as e:
        logger.error(f"Failed to save secrets config: {e}")
        return False


def set_secret(key: str, value: str) -> bool:
    """
    Set a secret value.

    Args:
        key: The secret key name
        value: The secret value

    Returns:
        bool: True if successful, False otherwise
    """
    logger.debug(f"Setting secret: {key}")
    config = load_secrets_config()
    config[key] = value
    result = save_secrets_config(config)
    if result:
        logger.info(f"Secret saved: {key}")
    return result


def get_secret(key: str) -> str | None:
    """
    Get a secret value.

    Args:
        key: The secret key name

    Returns:
        Optional[str]: The secret value if found, None otherwise
    """
    config = load_secrets_config()
    value = config.get(key)
    if value:
        logger.debug(f"Secret found: {key}")
    else:
        logger.debug(f"Secret not found: {key}")
    return value


def delete_secret(key: str) -> bool:
    """
    Delete a secret.

    Args:
        key: The secret key name

    Returns:
        bool: True if deleted, False if not found
    """
    config = load_secrets_config()

    if key in config:
        del config[key]
        return save_secrets_config(config)

    return False


def list_secrets() -> list:
    """
    List all configured secret keys.

    Returns:
        list: List of secret key names
    """
    config = load_secrets_config()
    return list(config.keys())


def secret_exists(key: str) -> bool:
    """
    Check if a secret exists.

    Args:
        key: The secret key name

    Returns:
        bool: True if the secret exists, False otherwise
    """
    config = load_secrets_config()
    return key in config
