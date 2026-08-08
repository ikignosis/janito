"""
CLI-facing config helpers.

These functions implement the ``--set`` / ``--get`` / ``--unset`` CLI
operations on ``~/.janito/config.json``: resolving provider-scoped keys,
coercing values (ints/bools), normalizing API types and validating provider
names.  They were extracted from :mod:`janito.general_config` (which
re-exports them) so the core config storage module stays focused on read/write
primitives.
"""

import json
import logging

from .general_config import (
    BOOL_VALUED_KEYS,
    INT_VALUED_KEYS,
    PROVIDER_SCOPED_KEYS,
    determine_provider,
    get_config_path,
    get_config_value,
    normalize_api_type,
    set_config_value,
    unset_config_value,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


class ProviderRequiredError(ValueError):
    """Raised when a provider-scoped config key is used without a provider.

    This happens when a key such as ``model`` is set/get/unset via the CLI but
    the provider cannot be determined (neither ``--provider`` nor a configured
    ``provider`` value is available).
    """


def _resolve_provider_scoped_key(key: str, cli_provider: str | None = None) -> str:
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


def _coerce_int_value(key: str, value) -> int:
    """Coerce a config value to an integer, raising ValueError on failure."""
    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"Config key '{key}' requires an integer value, got: {value!r}"
        )


def _coerce_bool_value(key: str, value) -> bool:
    """Coerce a config value to a boolean, raising ValueError on failure."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"Config key '{key}' requires a boolean value, got: {value!r}")
    return bool(value)


def set_config_from_cli(
    key_value: str, cli_provider: str | None = None
) -> tuple[str, str]:
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
    if "=" not in key_value:
        raise ValueError("--set requires KEY=VALUE format")

    key, value = key_value.split("=", 1)
    key = key.strip()
    value = value.strip()

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)

    # Validate provider name against supported providers (those that map to a
    # base URL) and normalize it to the canonical casing.
    if key == "provider":
        from .provider_config import validate_provider_name

        value = validate_provider_name(value)

    # Coerce values for keys that should be stored as integers.
    base_key = key.rsplit(".", 1)[-1]
    if base_key in INT_VALUED_KEYS:
        value = _coerce_int_value(key, value)

    # Coerce values for keys that should be stored as booleans (accepts
    # true/false/1/0/yes/no/on/off in any case).
    if base_key in BOOL_VALUED_KEYS:
        value = _coerce_bool_value(key, value)

    # Normalize API type values to their canonical casing (accepts
    # completions/responses/... in any case) and reject anything else, so a
    # typo is reported when the value is set rather than at the first API
    # call. Native-SDK API types (e.g. "Anthropic") also require their
    # optional package to be installed: when it is missing, the change is
    # aborted (nothing is written) with a message naming the package.
    if base_key == "api-type":
        value = normalize_api_type(value)
        from .provider_config import ensure_api_type_available

        ensure_api_type_available(value)

    set_config_value(key, value)

    return key, value


def get_config_from_cli(key: str, cli_provider: str | None = None) -> str | None:
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
    if not get_config_path().exists():
        raise FileNotFoundError(f"Config file not found: {get_config_path()}")

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)

    # Use get_config_value which handles the nested structure
    value = get_config_value(key)
    if value is None:
        return None

    # Convert non-string values to string for printing
    if not isinstance(value, str):
        return json.dumps(value)
    return value


def unset_config_key_from_cli(key: str, cli_provider: str | None = None) -> bool:
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
