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


def normalize_provider(provider: Optional[str]) -> Optional[str]:
    """Normalize a provider name for use as a config key prefix.

    Args:
        provider: The raw provider name (may be None)

    Returns:
        The lowercased/stripped provider name, or None if empty/None
    """
    if not provider:
        return None
    normalized = provider.strip().lower()
    return normalized or None


def determine_provider(cli_provider: Optional[str] = None) -> Optional[str]:
    """Determine the provider used for provider-scoped config (e.g. model).

    Unlike :func:`get_active_provider`, this does *not* fall back to a default
    provider. It is used for operations (such as ``--set model``) where a
    provider must be explicitly known.

    Priority:
    1. ``--provider`` CLI argument
    2. ``provider`` value from config.json

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        The normalized provider name, or None if it cannot be determined
    """
    provider = normalize_provider(cli_provider)
    if provider:
        return provider
    return normalize_provider(load_provider_from_config())


def model_config_key(provider: str) -> str:
    """Return the config key used to store the model for a given provider.

    Models are stored per-provider using the ``<provider>.model`` key so that
    each provider can have its own default model.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"openai.model"``
    """
    return f"{normalize_provider(provider)}.model"


def endpoint_config_key(provider: str) -> str:
    """Return the config key used to store the endpoint for a given provider.

    Endpoints are stored per-provider using the ``<provider>.endpoint`` key so
    that each provider can have its own endpoint override.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``"custom.endpoint"``
    """
    return f"{normalize_provider(provider)}.endpoint"


def load_model_from_config(cli_provider: Optional[str] = None) -> Optional[str]:
    """Load the model name for the active provider from ~/.janito/config.json.

    The model is stored under a provider-scoped key (``<provider>.model``) so
    that different providers can each have their own default model.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: Model name from config, or None if not found or provider unknown
    """
    provider = determine_provider(cli_provider)
    if not provider:
        return None
    return get_config_value(model_config_key(provider))


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


def load_endpoint_from_config(cli_provider: Optional[str] = None) -> Optional[str]:
    """Load custom endpoint URL from ~/.janito/config.json if it exists.

    This is used for the 'custom' provider or to override provider base URLs.

    The endpoint is stored under a provider-scoped key
    (``<provider>.endpoint``) so that different providers can each have their
    own endpoint. The provider is resolved from ``cli_provider`` first, then
    from the configured ``provider`` value.

    For backward compatibility, the legacy top-level ``endpoint`` key is still
    honored as a fallback when no provider-scoped endpoint is set.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: Endpoint URL from config, or None if not found or provider unknown
    """
    provider = determine_provider(cli_provider)
    if provider:
        value = get_config_value(endpoint_config_key(provider))
        if value is not None:
            return value
    # Backward compatibility: legacy top-level 'endpoint' key
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


# Config keys that are stored per-provider (as ``<provider>.<key>``)
PROVIDER_SCOPED_KEYS = {"model", "endpoint"}


class ProviderRequiredError(ValueError):
    """Raised when a provider-scoped config key is used without a provider.

    This happens when a key such as ``model`` is set/get/unset via the CLI but
    the provider cannot be determined (neither ``--provider`` nor a configured
    ``provider`` value is available).
    """


def _resolve_provider_scoped_key(key: str, cli_provider: Optional[str] = None) -> str:
    """Resolve a provider-scoped config key (e.g. ``model``) to its full key.

    Args:
        key: The config key requested (e.g. ``model``)
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        The full provider-scoped key (e.g. ``openai.model``)

    Raises:
        ProviderRequiredError: If the key is provider-scoped but the provider
            cannot be determined
    """
    provider = determine_provider(cli_provider)
    if not provider:
        raise ProviderRequiredError(
            f"Cannot determine provider for config key '{key}'. "
            f"Set one first with: janito --set provider=<name> "
            f"or pass --provider <name>."
        )
    return f"{provider}.{key}"


def set_config_from_cli(key_value: str, cli_provider: Optional[str] = None) -> tuple[str, str]:
    """Set a config key-value pair from CLI input.

    Provider-scoped keys (such as ``model``) are stored under a
    ``<provider>.<key>`` key so each provider can have its own value. The
    provider is taken from ``--provider`` or the configured ``provider`` value.

    Args:
        key_value: A string in the format "KEY=VALUE"
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        tuple: (key, value) that was set. For provider-scoped keys the returned
            key is the full provider-scoped key (e.g. ``openai.model``).

    Raises:
        ValueError: If the format is invalid
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
    """
    if '=' not in key_value:
        raise ValueError("--set requires KEY=VALUE format")

    key, value = key_value.split('=', 1)
    key = key.strip()
    value = value.strip()

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)

    set_config_value(key, value)

    return key, value


def get_config_from_cli(key: str, cli_provider: Optional[str] = None) -> Optional[str]:
    """Get a config value from CLI.

    Provider-scoped keys (such as ``model``) are read from the
    ``<provider>.<key>`` key. The provider is taken from ``--provider`` or the
    configured ``provider`` value.

    Args:
        key: The config key to retrieve
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        The config value, or None if not found

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file contains invalid JSON
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    value = config.get(key)
    if value is None:
        return None

    # Convert non-string values to string for printing
    if not isinstance(value, str):
        return json.dumps(value)
    return value


def unset_config_key_from_cli(key: str, cli_provider: Optional[str] = None) -> bool:
    """Remove a config value by key from CLI.

    Provider-scoped keys (such as ``model``) are removed from the
    ``<provider>.<key>`` key. The provider is taken from ``--provider`` or the
    configured ``provider`` value.

    Args:
        key: The config key to remove
        cli_provider: Provider passed via ``--provider`` (may be None)

    Returns:
        bool: True if the key was removed, False if it didn't exist

    Raises:
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
    """
    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)
    return unset_config_value(key)
