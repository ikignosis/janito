"""
Authentication utilities for LLM providers.
"""

import sys


def handle_missing_api_key(provider_name: str, env_var_name: str) -> None:
    """
    Handle missing API key by printing error message and exiting.

    Args:
        provider_name: Name of the provider (e.g., 'alibaba', 'openai')
        env_var_name: Environment variable name (e.g., 'ALIBABA_API_KEY')
    """
    if provider_name == "moonshot":
        print(
            f"[ERROR] You exceeded your current token quota for Moonshot. Please check your account balance at:"
        )
        print(f"  https://platform.moonshot.ai/console/pay")
        print()
        print(f"To set a new API key, use:")
        print(f"  janito --set-api-key YOUR_NEW_API_KEY -p moonshot")
    else:
        print(
            f"[ERROR] No API key found for provider '{provider_name}'. Please set the API key using:"
        )
        print(f"  janito --set-api-key YOUR_API_KEY -p {provider_name}")
        print(f"Or set the {env_var_name} environment variable.")
    sys.exit(1)
