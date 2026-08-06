"""
General configuration module for managing ~/.janito/config.json.

This module provides a centralized interface for all config.json-related operations.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .auth_config import get_default_provider
from .config_dir import get_config_dir

# Configure logger for this module
logger = logging.getLogger(__name__)


# Default config file path. Retained for backward compatibility; prefer
# :func:`get_config_path` which honors the runtime -c/--config-dir override.
CONFIG_PATH = get_config_dir() / "config.json"

# Config keys that are stored per-provider (as ``<provider>.<key>``)
PROVIDER_SCOPED_KEYS = {
    "model",
    "endpoint",
    "max-output-tokens",
    "reasoning-level",
    "api-type",
}

# Config keys whose values should be coerced to int when set via CLI.
INT_VALUED_KEYS = {"max-output-tokens"}


def get_config_path() -> Path:
    """Get the path to the config.json file.

    Returns:
        Path: Path to <config-dir>/config.json (defaults to ~/.janito/config.json)
    """
    return get_config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    """Load the entire config.json file.

    Returns:
        Dict containing the config, or empty dict if file doesn't exist or is invalid
    """
    config_path = get_config_path()
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.debug(f"Loaded config from {config_path}: {list(config.keys())}")
            return config
    except FileNotFoundError:
        logger.debug(f"Config file not found: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}


def save_config(config: dict[str, Any]) -> None:
    """Save the config dictionary to config.json.

    Args:
        config: Dictionary to save to config.json

    Raises:
        IOError: If unable to write to the config file
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.debug(f"Saved config to {config_path}")


def get_config_value(key: str) -> Any | None:
    """Get a config value by key.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it reads from the nested
    providers structure.

    Args:
        key: The config key to retrieve

    Returns:
        The config value, or None if not found or config file doesn't exist
    """
    config = load_config()

    # Check if this is a provider-scoped key (e.g., "openai.model")
    if "." in key:
        parts = key.split(".", 1)
        if len(parts) == 2:
            provider, subkey = parts
            providers = config.get("providers", {})
            if isinstance(providers, dict) and provider in providers:
                provider_config = providers[provider]
                if isinstance(provider_config, dict):
                    value = provider_config.get(subkey)
                    logger.debug(
                        f"Getting config '{key}': {value if value is None else '(set)'}"
                    )
                    return value

    # Fall back to flat key lookup
    value = config.get(key)
    logger.debug(f"Getting config '{key}': {value if value is None else '(set)'}")
    return value


def set_config_value(key: str, value: Any) -> None:
    """Set a config value.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it writes to the nested
    providers structure.

    Args:
        key: The config key to set
        value: The value to set
    """
    logger.debug(f"Setting config '{key}' = {value}")
    config = load_config()

    # Check if this is a provider-scoped key (e.g., "openai.model")
    if "." in key:
        parts = key.split(".", 1)
        if len(parts) == 2:
            provider, subkey = parts
            if subkey in PROVIDER_SCOPED_KEYS:
                # Write to nested providers structure
                providers = config.get("providers")
                if not isinstance(providers, dict):
                    providers = {}
                    config["providers"] = providers
                provider_config = providers.get(provider)
                if not isinstance(provider_config, dict):
                    provider_config = {}
                    providers[provider] = provider_config
                provider_config[subkey] = value
                save_config(config)
                return

    # Fall back to flat key storage
    config[key] = value
    save_config(config)


def unset_config_value(key: str) -> bool:
    """Remove a config value by key.

    Supports both flat keys and provider-scoped keys in the nested structure.
    For provider-scoped keys (e.g., "openai.model"), it removes from the nested
    providers structure.  If the provider dict becomes empty after removal, the
    provider entry itself is also removed.

    Args:
        key: The config key to remove

    Returns:
        bool: True if the key was removed, False if it didn't exist
    """
    config = load_config()

    # Check if this is a provider-scoped key (e.g., "openai.model")
    if "." in key:
        parts = key.split(".", 1)
        if len(parts) == 2:
            provider, subkey = parts
            if subkey in PROVIDER_SCOPED_KEYS:
                providers = config.get("providers")
                if not isinstance(providers, dict):
                    logger.debug(f"Config key not found for removal: {key}")
                    return False
                provider_config = providers.get(provider)
                if not isinstance(provider_config, dict):
                    logger.debug(f"Config key not found for removal: {key}")
                    return False
                if subkey not in provider_config:
                    logger.debug(f"Config key not found for removal: {key}")
                    return False
                del provider_config[subkey]
                if not provider_config:
                    del providers[provider]
                if not providers:
                    del config["providers"]
                save_config(config)
                logger.info(f"Removed config key: {key}")
                return True

    # Fall back to flat key removal
    if key in config:
        del config[key]
        save_config(config)
        logger.info(f"Removed config key: {key}")
        return True
    logger.debug(f"Config key not found for removal: {key}")
    return False


def load_provider_from_config() -> str | None:
    """Load provider name from ~/.janito/config.json if it exists.

    Returns:
        str: Provider name from config, or None if not found
    """
    return get_config_value("provider")


def normalize_provider(provider: str | None) -> str | None:
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


def determine_provider(cli_provider: str | None = None) -> str | None:
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


def reasoning_level_config_key(provider: str) -> str:
    """Return the config key used to store the reasoning level for a provider.

    Reasoning levels are stored per-provider using the
    ``<provider>.reasoning-level`` key so that each provider can have its own
    reasoning depth (e.g. ``low``/``medium``/``xhigh`` for Qwen3.8-Max).

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``\"alibaba.reasoning-level\"``
    """
    return f"{normalize_provider(provider)}.reasoning-level"


def api_type_config_key(provider: str) -> str:
    """Return the config key used to store the API type for a provider.

    API types are stored per-provider using the ``<provider>.api-type`` key
    (``\"Responses\"`` or ``\"Completions\"``) so that each provider can select
    which API it talks to.

    Args:
        provider: The provider name

    Returns:
        The provider-scoped config key, e.g. ``\"openai.api-type\"``
    """
    return f"{normalize_provider(provider)}.api-type"


def normalize_api_type(value: str) -> str:
    """Normalize an API type value to its canonical form.

    Accepts ``responses``/``completions`` in any casing (e.g. the values used
    with ``--set api-type=...``) and returns the canonical ``\"Responses\"`` or
    ``\"Completions\"``.

    Args:
        value: The raw API type value

    Returns:
        The canonical API type: ``\"Responses\"`` or ``\"Completions\"``

    Raises:
        ValueError: If the value is neither ``Responses`` nor ``Completions``
    """
    api_type = str(value).strip().capitalize()
    if api_type not in ("Responses", "Completions"):
        raise ValueError(
            f"Unsupported API type '{value}'. Supported values: Responses, Completions"
        )
    return api_type


def load_model_from_config(cli_provider: str | None = None) -> str | None:
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


def load_max_output_tokens(cli_provider: str | None = None) -> int | None:
    """Load max output tokens from ~/.janito/config.json if it exists.

    This value is used as the maximum output-token limit (``max_tokens`` /
    ``max_completion_tokens``) for API calls. It is stored per-provider under
    the nested providers structure (e.g. providers.openai.max-output-tokens).

    For backward compatibility, the legacy ``<provider>.context-window-size``
    and ``<provider>.context_window_size`` keys are still honored when the new
    key is not set.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        int: Max output tokens from config, or None if not found
    """
    provider = determine_provider(cli_provider)
    if not provider:
        return None
    # Support both hyphenated and underscore formats in config
    key = f"{provider}.max-output-tokens"
    value = get_config_value(key)
    if value is not None:
        return int(value)
    key = f"{provider}.max_output_tokens"
    value = get_config_value(key)
    if value is not None:
        return int(value)
    # Backward compatibility: legacy context-window-size / context_window_size keys.
    key = f"{provider}.context-window-size"
    value = get_config_value(key)
    if value is not None:
        return int(value)
    key = f"{provider}.context_window_size"
    value = get_config_value(key)
    if value is not None:
        return int(value)
    return None


def load_reasoning_level(cli_provider: str | None = None) -> str | None:
    """Load the reasoning level for the active provider from config.json.

    The reasoning level is stored under a provider-scoped key
    (``<provider>.reasoning-level``) so that different providers can each have
    their own reasoning depth (e.g. ``low``/``medium``/``xhigh`` for
    Qwen3.8-Max).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: The reasoning level from config, or None if not found
    """
    provider = determine_provider(cli_provider)
    if not provider:
        return None
    value = get_config_value(reasoning_level_config_key(provider))
    if value is not None:
        return str(value)
    return None


def load_api_type(cli_provider: str | None = None) -> str | None:
    """Load the API type for the active provider from config.json.

    The API type is stored under a provider-scoped key
    (``<provider>.api-type``) so that different providers can each select
    which API they talk to (``"Responses"`` or ``"Completions"``).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: The API type from config, or None if not found
    """
    provider = determine_provider(cli_provider)
    if not provider:
        return None
    value = get_config_value(api_type_config_key(provider))
    if value is not None:
        return str(value)
    return None


def load_endpoint_from_config(cli_provider: str | None = None) -> str | None:
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
    """Mask an API key, preserving its length for display.

    The returned string has the same length as ``api_key``: the first few and
    last few characters are shown and the middle is filled with ``.`` so the
    output never reveals the full key.

    Args:
        api_key: The API key to mask

    Returns:
        str: Masked API key with the same length as the input, or
            ``(not set)`` when the key is empty.
    """
    if not api_key:
        return "(not set)"
    prefix_len = 6
    suffix_len = 4
    n = len(api_key)
    middle = n - prefix_len - suffix_len
    if middle <= 0:
        # Key too short to keep both ends while preserving length; mask it all.
        return "." * n
    return f"{api_key[:prefix_len]}{'.' * middle}{api_key[-suffix_len:]}"


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
    default_provider = get_default_provider()
    if default_provider:
        logger.debug(f"Active provider from auth defaults: {default_provider}")
        return default_provider

    # 4. Fall back to 'openai'
    logger.debug("No provider found, using fallback: openai")
    return "openai"


def resolve_api_type(
    cli_api_type: str | None = None, cli_provider: str | None = None
) -> str:
    """Resolve the effective API type ("Responses" or "Completions").

    The API type selects which client the CLI talks to: the Responses API
    (``client.responses.create``, server-side conversation state) or the Chat
    Completions API (``client.chat.completions.create``, client-side history).

    Resolution rules:
      - api_type: ``--api-type`` CLI arg, then the provider's configured
        value (``--set api-type=...``), and finally the provider's built-in
        default from ``PROVIDER_INFO.supported_api_types`` (its **first**
        entry, e.g. ``"Responses"`` for OpenAI).
      - provider: ``--provider`` (``cli_provider``), then the configured
        provider (config.json), then auth.json's default, then ``"openai"``.

    Args:
        cli_api_type: API type passed via ``--api-type`` (highest priority).
            May be None.
        cli_provider: Provider passed via ``--provider``. May be None.

    Returns:
        The canonical API type: ``"Responses"`` or ``"Completions"``.

    Raises:
        ValueError: If an explicitly configured API type is neither
            ``"Responses"`` nor ``"Completions"``.
    """
    from .provider_config import get_default_api_type_from_provider

    raw = cli_api_type or load_api_type(cli_provider)
    if raw:
        try:
            return normalize_api_type(raw)
        except ValueError:
            logger.error(f"Unsupported API type: {raw}")
            raise

    provider = cli_provider or get_active_provider()
    default = get_default_api_type_from_provider(provider)
    return default or "Completions"


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
        try:
            value = int(value)
        except ValueError:
            raise ValueError(
                f"Config key '{key}' requires an integer value, got: {value!r}"
            )

    # Normalize API type values to their canonical casing (accepts
    # completions/responses in any case) and reject anything else, so a typo
    # is reported when the value is set rather than at the first API call.
    if base_key == "api-type":
        value = normalize_api_type(value)

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
