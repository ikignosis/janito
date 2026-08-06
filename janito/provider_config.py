"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including default models, default max
output tokens, and base URLs (endpoints) for the API.

Provider Info:
{
    "openai": {
        "model": "gpt-4",
        "max_input_tokens": 128000,
        "max_output_tokens": 128000,
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
#   - "model": the model used when the user has not configured one.
#     ``None`` means the provider has no sensible default and the user must
#     set a model explicitly (e.g. the "custom" provider).
#   - "max_input_tokens": the maximum input-token (context window)
#     limit used as the built-in default. ``None`` means there is no built-in
#     limit (the caller falls back to its own default).
#   - "max_output_tokens": the maximum output-token limit (max_tokens
#     / max_completion_tokens) used when the user has not configured one.
#     ``None`` means there is no built-in limit (the caller falls back to its
#     own default).
#   - "reasoning_level": the reasoning level/effort used by default for
#     the provider's default model when it supports configurable reasoning
#     depth. ``None`` (or absent) means there is no built-in default.
#   - "supported_reasoning_levels": the list of reasoning levels supported by
#     the provider's default model, each with an ``effort`` key and a
#     human-readable ``description``. Absent when the model has no
#     configurable reasoning.
#   - "thinking": whether thinking mode (``extra_body=
#     {'enable_thinking': True}``) is enabled by default for the provider's
#     models. ``True`` for providers whose models reason by default (DeepSeek,
#     Alibaba/Qwen); absent (or ``False``) for the rest. The CLI ``--thinking``
#     flag still forces it on explicitly.
#   - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
#     OpenAI API endpoint (no custom base URL needed); the special
#     ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
PROVIDER_INFO: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": {
        "model": "gpt-4",
        "max_input_tokens": 128000,
        "max_output_tokens": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    "minimax": {
        "model": "MiniMax-M3",
        "max_input_tokens": 128000,
        "max_output_tokens": 511000,  # 512k
        "endpoint": "https://api.minimax.io/v1",
    },
    "xiaomi": {
        "model": "mimo-v2.5",
        "max_input_tokens": 128000,
        "max_output_tokens": 120000,  # 128k
        "endpoint": "https://api.xiaomimimo.com/v1",
    },
    "moonshot": {
        "model": "kimi-k3-256k",
        "max_input_tokens": 128000,
        "max_output_tokens": 250000,  # 256k
        "endpoint": "https://api.moonshot.ai/v1",
    },
    "alibaba": {
        "model": "qwen3.8-max",
        "max_input_tokens": 1000000,  # 1M
        "max_output_tokens": 131072,
        "reasoning_level": "xhigh",
        "thinking": True,  # Qwen models reason by default
        "supported_reasoning_levels": [
            {
                "effort": "low",
                "description": "Fast responses with lighter reasoning",
            },
            {
                "effort": "medium",
                "description": "Greater reasoning depth for complex problems",
            },
            {
                "effort": "xhigh",
                "description": "Extra high reasoning depth for complex problems",
            },
        ],
        "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    },
    "zai": {
        "model": "glm-5.2",
        "max_input_tokens": 128000,
        "max_output_tokens": 1000000,  # 1M
        "endpoint": "https://api.z.ai/api/paas/v4/",
    },
    "deepseek": {
        "model": "deepseek-v4-flash",
        "max_input_tokens": 1000000,  # 1M
        "max_output_tokens": 393216,  # 384k
        "thinking": True,  # DeepSeek models reason by default
        "endpoint": "https://api.deepseek.com",
    },
    "xai": {
        "model": "grok-4",
        "max_input_tokens": 128000,
        "max_output_tokens": 131072,
        "endpoint": "https://api.x.ai/v1",
    },
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model.
    "custom": {
        "model": None,
        "max_input_tokens": None,
        "max_output_tokens": None,
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
    return info.get("model")


def get_default_max_output_tokens_from_provider(provider: str) -> int | None:
    """
    Get the built-in default max output tokens for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default max output tokens if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("max_output_tokens")


def get_default_max_input_tokens_from_provider(provider: str) -> int | None:
    """
    Get the built-in default max input tokens for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default max input tokens if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("max_input_tokens")


def get_default_reasoning_level_from_provider(provider: str) -> str | None:
    """
    Get the built-in default reasoning level for a given provider name.

    This is the reasoning level/effort used by default for the provider's
    default model when it supports configurable reasoning depth (e.g. ``xhigh``
    for Alibaba's ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The default reasoning level if the provider has one, ``None``
        otherwise (either the provider is unknown or it has no default).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("reasoning_level")


def get_supported_reasoning_levels_from_provider(provider: str) -> list | None:
    """
    Get the supported reasoning levels for a given provider name.

    Each entry is a dict with an ``effort`` key and a human-readable
    ``description``, describing the reasoning depths the provider's default
    model supports (e.g. ``low``/``medium``/``xhigh`` for Alibaba's
    ``qwen3.8-max``).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The list of supported reasoning levels if the provider declares them,
        ``None`` otherwise (either the provider is unknown or it has no
        configurable reasoning).
    """
    info = get_provider_info(provider)
    if info is None:
        return None
    return info.get("supported_reasoning_levels")


def get_default_thinking_from_provider(provider: str) -> bool:
    """
    Get the built-in default for thinking mode for a given provider name.

    Providers whose models reason by default (DeepSeek, Alibaba/Qwen) declare
    ``thinking: True``; everyone else falls back to ``False``. The CLI
    ``--thinking`` flag still forces thinking on explicitly.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider's models use thinking mode by default, False
        otherwise (including unknown providers).
    """
    info = get_provider_info(provider)
    if info is None:
        return False
    return bool(info.get("thinking"))


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
