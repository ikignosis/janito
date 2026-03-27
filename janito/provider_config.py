"""
Provider configuration management for Janito CLI.

Handles provider-specific settings including base URLs for API endpoints.

Provider Base URLs:
{
    "minimax": "https://api.minimax.io/v1",
    "openai": None,  # Standard OpenAI - no base_url needed
    "anthropic": "https://api.anthropic.com/v1",
    # ... more providers
}
"""

from typing import Dict, Optional


# Provider to Base URL mapping
# None means the standard OpenAI API endpoint (no custom base URL needed)
# "custom" is a special case that requires an endpoint from --endpoint or config
PROVIDER_BASE_URLS: Dict[str, Optional[str]] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": None,  # Standard OpenAI - no base_url needed
    "minimax": "https://api.minimax.io/v1",
    "xiaomi": "https://api.xiaomimimo.com/v1",
    "moonshot": "https://api.moonshot.ai/v1",
    "alibaba": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "zai": "https://api.z.ai/api/paas/v4/",
    "custom": "CUSTOM_ENDPOINT",  # Special marker - endpoint must be provided via --endpoint or config
}


def get_base_url_from_provider(provider: str) -> Optional[str]:
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


CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


def list_supported_providers() -> list:
    """
    List all supported providers.
    
    Returns:
        List of provider names
    """
    return list(PROVIDER_BASE_URLS.keys())
