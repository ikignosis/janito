"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including default models, default context
window sizes, and base URLs (endpoints) for the API.

Provider Info:
{
    "openai": {
        "default_model": "gpt-4",
        "default_context_window_size": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    # ... more providers
}
"""

# Marker for the special "custom" provider: its endpoint is not built in and
# must be supplied via config (--set endpoint).
CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


# Per-provider built-in defaults.
#
# Each entry describes a supported provider and carries more information than
# just the endpoint (the old ``PROVIDER_BASE_URLS`` only mapped a provider to
# its base URL). The fields are:
#
#   - "default_model": the model used when the user has not configured one.
#     ``None`` means the provider has no sensible default and the user must
#     set a model explicitly (e.g. the "custom" provider).
#   - "default_context_window_size": the context-window / max-tokens limit
#     used when the user has not configured one. ``None`` means there is no
#     built-in limit (the caller falls back to its own default).
#   - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
#     OpenAI API endpoint (no custom base URL needed); the special
#     ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
PROVIDER_INFO: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": {
        "default_model": "gpt-4",
        "default_context_window_size": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    "minimax": {
        "default_model": "MiniMax-M3",
        "default_context_window_size": 511000,  # 512k
        "endpoint": "https://api.minimax.io/v1",
    },
    "xiaomi": {
        "default_model": "mimo-v2.5",
        "default_context_window_size": 120000,  # 128k
        "endpoint": "https://api.xiaomimimo.com/v1",
    },
    "moonshot": {
        "default_model": "kimi-k3-256k",
        "default_context_window_size": 250000,  # 256k
        "endpoint": "https://api.moonshot.ai/v1",
    },
    "alibaba": {
        "default_model": "qwen3.8-max-preview",
        "default_context_window_size": 131072,
        "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    },
    "zai": {
        "default_model": "glm-5.2",
        "default_context_window_size": 1000000,  # 1M
        "endpoint": "https://api.z.ai/api/paas/v4/",
    },
    "xai": {
        "default_model": "grok-4",
        "default_context_window_size": 131072,
        "endpoint": "https://api.x.ai/v1",
    },
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model.
    "custom": {
        "default_model": None,
        "default_context_window_size": None,
        "endpoint": CUSTOM_ENDPOINT_MARKER,
    },
}


def get_provider_info(provider: str) -> dict | None:
    """
    Get the full ``PROVIDER_INFO`` entry for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The provider info dict if found, ``None`` otherwise.
    """
    if not provider:
        return None

    # Try exact match first, then case-insensitive.
    if provider in PROVIDER_INFO:
        return PROVIDER_INFO[provider]

    provider_lower = provider.lower()
    for key, value in PROVIDER_INFO.items():
        if key.lower() == provider_lower:
            return value

    return None


def get_base_url_from_provider(provider: str) -> str | None:
    """
    Get the base URL (endpoint) for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The base URL if found, None otherwise.
        For "custom" provider, returns the "CUSTOM_ENDPOINT" marker.
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("endpoint")


def get_default_model_from_provider(provider: str) -> str | None:
    """
    Get the built-in default model for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default model if the provider has one, ``None`` otherwise (either
        the provider is unknown or it has no default model, e.g. "custom").
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("default_model")


def get_default_context_window_size_from_provider(provider: str) -> int | None:
    """
    Get the built-in default context window size for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default context window size if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("default_context_window_size")


def canonical_provider_name(provider: str) -> str | None:
    """
    Return the canonical (correctly cased) name for a supported provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The canonical provider name as used in ``PROVIDER_INFO`` if the
        provider is supported, otherwise ``None``.
    """
    if not provider:
        return None

    provider_lower = provider.strip().lower()
    if not provider_lower:
        return None

    for key in PROVIDER_INFO:
        if key.lower() == provider_lower:
            return key
    return None


def is_supported_provider(provider: str) -> bool:
    """
    Check if a provider name is a supported provider (i.e. it maps to an entry
    in :data:`PROVIDER_INFO`).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is supported, False otherwise
    """
    return canonical_provider_name(provider) is not None


def is_custom_provider(provider: str) -> bool:
    """
    Check if a provider is the special "custom" provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is "custom", False otherwise
    """
    if not provider:
        return False
    return provider.lower() == "custom"


def validate_provider_name(provider: str) -> str:
    """
    Validate a provider name against the supported providers and return its
    canonical form.

    A provider is considered valid only if it maps to an entry in
    :data:`PROVIDER_INFO`.

    Args:
        provider: The provider name to validate (case-insensitive)

    Returns:
        The canonical (correctly cased) provider name.

    Raises:
        ValueError: If the provider is not supported. The message enumerates
            the supported providers.
    """
    canonical = canonical_provider_name(provider)
    if canonical is None:
        supported = ", ".join(sorted(PROVIDER_INFO.keys()))
        raise ValueError(
            f"Unknown provider '{provider}'. Supported providers: {supported}"
        )
    return canonical


def list_supported_providers() -> list:
    """
    List all supported providers.

    Returns:
        List of provider names
    """
    return list(PROVIDER_INFO.keys())
