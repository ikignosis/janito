"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including base URLs for API endpoints.

Provider Base URLs:
{
    "minimax": "https://api.minimax.io/v1",
    "openai": None,  # Standard OpenAI - no base_url needed
    # ... more providers
}
"""


# Provider to Base URL mapping
# None means the standard OpenAI API endpoint (no custom base URL needed)
# "custom" is a special case that requires an endpoint from config (--set endpoint)
PROVIDER_BASE_URLS: dict[str, str | None] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": None,  # Standard OpenAI - no base_url needed
    "minimax": "https://api.minimax.io/v1",
    "xiaomi": "https://api.xiaomimimo.com/v1",
    "moonshot": "https://api.moonshot.ai/v1",
    "alibaba": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "zai": "https://api.z.ai/api/paas/v4/",
    "xai": "https://api.x.ai/v1",
    "custom": "CUSTOM_ENDPOINT",  # Special marker - endpoint must be provided via config (--set endpoint)
}


def get_base_url_from_provider(provider: str) -> str | None:
    """
    Get the base URL for a given provider name.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The base URL if found, None otherwise
        For "custom" provider, returns "CUSTOM_ENDPOINT" marker
    """
    if not provider:
        return None

    # Try exact match first, then case-insensitive
    if provider in PROVIDER_BASE_URLS:
        return PROVIDER_BASE_URLS[provider]

    # Try case-insensitive match
    provider_lower = provider.lower()
    for key, value in PROVIDER_BASE_URLS.items():
        if key.lower() == provider_lower:
            return value

    return None


def canonical_provider_name(provider: str) -> str | None:
    """
    Return the canonical (correctly cased) name for a supported provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The canonical provider name as used in ``PROVIDER_BASE_URLS`` if the
        provider is supported, otherwise ``None``.
    """
    if not provider:
        return None

    provider_lower = provider.strip().lower()
    if not provider_lower:
        return None

    for key in PROVIDER_BASE_URLS:
        if key.lower() == provider_lower:
            return key
    return None


def is_supported_provider(provider: str) -> bool:
    """
    Check if a provider name is a supported provider (i.e. it maps to an entry
    in the provider -> base URL mapping).

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

    A provider is considered valid only if it maps to an entry in the
    provider -> base URL mapping (:data:`PROVIDER_BASE_URLS`).

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
        supported = ", ".join(sorted(PROVIDER_BASE_URLS.keys()))
        raise ValueError(
            f"Unknown provider '{provider}'. Supported providers: {supported}"
        )
    return canonical


CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


def list_supported_providers() -> list:
    """
    List all supported providers.

    Returns:
        List of provider names
    """
    return list(PROVIDER_BASE_URLS.keys())
