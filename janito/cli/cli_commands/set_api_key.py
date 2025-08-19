"""
CLI Command: Set API key for the current or selected provider
"""

from janito.provider_config import set_api_key
from janito.llm.auth import LLMAuthManager
from janito.providers.registry import LLMProviderRegistry


def handle_set_api_key(args):
    api_key = getattr(args, "set_api_key", None)
    provider = getattr(args, "provider", None)
    if not provider:
        print("Error: --set-api-key requires -p/--provider to be specified.")
        return

    # Validate provider name
    if provider not in LLMProviderRegistry.list_providers():
        valid_providers = LLMProviderRegistry.list_providers()
        print(
            f"Error: Unknown provider '{provider}'. Valid providers are: {', '.join(valid_providers)}"
        )
        return

    try:
        set_api_key(provider, api_key)
        auth_manager = LLMAuthManager()
        print(
            f"API key set for provider '{provider}'. Auth file updated: {auth_manager._auth_file}"
        )
    except ValueError as e:
        print(f"Error: {e}")
