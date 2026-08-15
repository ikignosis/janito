"""
CLI-facing config helpers.

These functions implement the ``--set`` / ``--get`` / ``--unset`` CLI
operations on ``~/.janito/config.json``: resolving provider-scoped and
model-scoped keys, coercing values (ints/bools), normalizing API types and
validating provider names.  They were extracted from
:mod:`janito.general_config` so the core config storage module stays focused
on read/write primitives.

Provider-scoped keys (``model``, ``endpoint``) land under
``providers.<provider>.<key>``; model-scoped keys (``max-output-tokens``,
``max-input-tokens``, ``reasoning-level``, ``api-type``,
``responses-in-server``) land under
``providers.<provider>.models.<model>.<key>``, where the model is the
provider's configured model or, failing that, its built-in default model.
"""

import json
import logging

from .config_keys import (
    BOOL_VALUED_KEYS,
    INT_VALUED_KEYS,
    MODEL_SCOPED_KEYS,
    PROVIDER_SCOPED_KEYS,
    model_scoped_config_key,
    normalize_api_type,
)
from .config_store import (
    get_config_path,
    get_config_paths,
    get_config_value,
    set_config_value,
    unset_config_value,
)
from .general_config import determine_provider

# Configure logger for this module
logger = logging.getLogger(__name__)


class ProviderRequiredError(ValueError):
    """Raised when a provider-scoped config key is used without a provider.

    This happens when a key such as ``model`` is set/get/unset via the CLI but
    the provider cannot be determined (neither ``--provider`` nor a configured
    ``provider`` value is available).
    """


class ModelRequiredError(ValueError):
    """Raised when a model-scoped config key is used without a resolvable model.

    This happens when a key such as ``max-output-tokens`` is set/get/unset
    via the CLI but neither the provider's configured model nor its built-in
    default model is available (e.g. the ``custom`` provider before
    ``--set model=<name>``).
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


def _resolve_model_scoped_key(
    key: str,
    cli_provider: str | None = None,
    cli_model: str | None = None,
) -> str:
    """Resolve a model-scoped config key to its full nested key.

    The value belongs to ``--model`` (``cli_model``) when given, else the
    provider's configured model (its ``<provider>.model`` value), else the
    provider's built-in default model (the provider config's
    ``default_model``).

    Args:
        key: The config key requested (e.g. ``max-output-tokens``)
        cli_provider: Provider passed via ``--provider`` (may be None)
        cli_model: Model passed via ``--model`` (may be None)

    Returns:
        The full model-scoped key (e.g.
        ``openai.models.gpt-5.6-luna.max-output-tokens``)

    Raises:
        ProviderRequiredError: If the provider cannot be determined
        ModelRequiredError: If no model can be resolved (e.g. ``custom``
            without a configured or default model)
    """
    from .config_loaders import load_model_from_config
    from .provider_accessors import get_default_model_from_provider

    provider = determine_provider(cli_provider)
    if not provider:
        raise ProviderRequiredError(
            f"Cannot determine provider for config key '{key}'. "
            f"Set one first with: janito --set provider=<name> "
            f"or pass --provider <name>."
        )
    model = (
        cli_model
        or load_model_from_config(provider)
        or get_default_model_from_provider(provider)
    )
    if not model:
        raise ModelRequiredError(
            f"Cannot determine the model for config key '{key}' "
            f"(provider '{provider}' has no configured or default model). "
            f"Set one first with: janito --provider {provider} --set model=<name> "
            f"or pass --model <name>."
        )
    return model_scoped_config_key(provider, model, key)


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
    key_value: str,
    cli_provider: str | None = None,
    cli_model: str | None = None,
) -> tuple[str, str]:
    """Set a config key-value pair from CLI input.

    Provider-scoped keys (such as ``model``) are stored under a
    ``<provider>.<key>`` key; model-scoped keys (such as
    ``max-output-tokens``) are stored under
    ``<provider>.models.<model>.<key>``, where the model is ``--model``,
    else the provider's configured model, else its built-in default model.
    The provider is taken from ``--provider`` or the configured
    ``provider`` value.

    Args:
        key_value: A string in the format "KEY=VALUE"
        cli_provider: Provider passed via ``--provider`` (may be None)
        cli_model: Model passed via ``--model`` (may be None; used to pick
            the model-scoped target model)

    Returns:
        tuple: (key, value) that was set. For scoped keys the returned key
            is the full nested key (e.g. ``openai.model`` or
            ``openai.models.gpt-5.6-luna.max-output-tokens``).

    Raises:
        ValueError: If the format is invalid
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
        ModelRequiredError: If a model-scoped key is used but no model can
            be resolved
    """
    if "=" not in key_value:
        raise ValueError("--set requires KEY=VALUE format")

    key, value = key_value.split("=", 1)
    key = key.strip()
    value = value.strip()

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)
    elif key in MODEL_SCOPED_KEYS:
        key = _resolve_model_scoped_key(key, cli_provider, cli_model)

    # Validate provider name against supported providers (those that map to a
    # base URL) and normalize it to the canonical casing.
    if key == "provider":
        from .provider_validation import validate_provider_name

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
        from .provider_accessors import ensure_api_type_available

        ensure_api_type_available(value)

    set_config_value(key, value)

    return key, value


def get_config_from_cli(
    key: str,
    cli_provider: str | None = None,
    cli_model: str | None = None,
) -> str | None:
    """Get a config value from CLI.

    Provider-scoped keys (such as ``model``) are read from the
    ``<provider>.<key>`` key; model-scoped keys (such as
    ``max-output-tokens``) from ``<provider>.models.<model>.<key>``. The
    provider is taken from ``--provider`` or the configured ``provider``
    value.

    Args:
        key: The config key to retrieve
        cli_provider: Provider passed via ``--provider`` (may be None)
        cli_model: Model passed via ``--model`` (may be None; used to pick
            the model-scoped target model)

    Returns:
        The config value, or None if not found

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file contains invalid JSON
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
        ModelRequiredError: If a model-scoped key is used but no model can
            be resolved
    """
    if not any(path.exists() for path in get_config_paths()):
        raise FileNotFoundError(f"Config file not found: {get_config_path()}")

    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)
    elif key in MODEL_SCOPED_KEYS:
        key = _resolve_model_scoped_key(key, cli_provider, cli_model)

    # Use get_config_value which handles the nested structure
    value = get_config_value(key)
    if value is None:
        return None

    # Convert non-string values to string for printing
    if not isinstance(value, str):
        return json.dumps(value)
    return value


def unset_config_key_from_cli(
    key: str,
    cli_provider: str | None = None,
    cli_model: str | None = None,
) -> bool:
    """Remove a config value by key from CLI.

    Provider-scoped keys (such as ``model``) are removed from the
    ``<provider>.<key>`` key; model-scoped keys (such as
    ``max-output-tokens``) from ``<provider>.models.<model>.<key>``. The
    provider is taken from ``--provider`` or the configured ``provider``
    value.

    Args:
        key: The config key to remove
        cli_provider: Provider passed via ``--provider`` (may be None)
        cli_model: Model passed via ``--model`` (may be None; used to pick
            the model-scoped target model)

    Returns:
        bool: True if the key was removed, False if it didn't exist

    Raises:
        ProviderRequiredError: If a provider-scoped key is used but the
            provider cannot be determined
        ModelRequiredError: If a model-scoped key is used but no model can
            be resolved
    """
    if key in PROVIDER_SCOPED_KEYS:
        key = _resolve_provider_scoped_key(key, cli_provider)
    elif key in MODEL_SCOPED_KEYS:
        key = _resolve_model_scoped_key(key, cli_provider, cli_model)
    return unset_config_value(key)
