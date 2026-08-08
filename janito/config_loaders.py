"""
Per-provider config loaders.

These helpers read provider-scoped values (``model``, ``max-output-tokens``,
``reasoning-level``, ``api-type``, ``responses-in-server``, ``endpoint``) from
``~/.janito/config.json``.  They were extracted from
:mod:`janito.general_config` (which re-exports them) so the core config
storage module stays focused on read/write primitives.
"""

import logging

from .general_config import (
    api_type_config_key,
    determine_provider,
    endpoint_config_key,
    get_config_value,
    model_config_key,
    reasoning_level_config_key,
    responses_in_server_config_key,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


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


def load_responses_in_server_from_config(
    cli_provider: str | None = None,
) -> bool | None:
    """Load the Responses-in-server override for a provider from config.json.

    The override is stored under a provider-scoped key
    (``<provider>.responses-in-server``) so that different providers can each
    decide whether their Responses API keeps conversation state server-side.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        bool: The configured override (``True``/``False``), or ``None`` when
            no override is stored (the provider's built-in default applies).
    """
    provider = determine_provider(cli_provider)
    if not provider:
        return None
    value = get_config_value(responses_in_server_config_key(provider))
    if value is None:
        return None
    # Tolerate string forms written by hand/older configs ("true"/"false").
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


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
