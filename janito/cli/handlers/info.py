"""Info and configuration display CLI handlers."""

import os
import sys

try:
    from ...general_config import (
        load_provider_from_config,
        load_model_from_config,
        load_endpoint_from_config,
        get_active_provider,
        get_config_path
    )
    from ...auth_config import get_api_key, get_auth_file_path, get_default_provider
    from ...provider_config import is_custom_provider, CUSTOM_ENDPOINT_MARKER
except ImportError:
    from janito.general_config import (
        load_provider_from_config,
        load_model_from_config,
        load_endpoint_from_config,
        get_active_provider,
        get_config_path
    )
    from janito.auth_config import get_api_key, get_auth_file_path, get_default_provider
    from janito.provider_config import is_custom_provider, CUSTOM_ENDPOINT_MARKER


def get_masked_api_key(api_key: str) -> str:
    """Mask an API key to show only first and last few characters.
    
    Args:
        api_key: The API key to mask
        
    Returns:
        str: Masked API key showing first 6 and last 4 characters
    """
    if not api_key:
        return "(not set)"
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:6]}...{api_key[-4:]}"


def handle_info(args) -> int:
    """Handle --info command.
    
    Prints information about the resolved configuration and exits.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success)
    """
    cli_provider = getattr(args, 'provider', None)
    
    # Determine resolved provider (priority: config.json > auth.json default > fallback)
    provider = None
    provider_source = ""
    
    # 1. Check CLI argument directly
    if cli_provider:
        provider = cli_provider
        provider_source = "CLI argument"
    # 2. Check config.json for provider
    else:
        config_provider = load_provider_from_config()
        if config_provider:
            provider = config_provider
            provider_source = "config.json"
        else:
            # 3. Check auth.json for default provider
            default_provider = get_default_provider()
            if default_provider:
                provider = default_provider
                provider_source = "auth.json (default)"
            else:
                # 4. Fall back to 'openai'
                provider = "openai"
                provider_source = "fallback"
    
    # Determine resolved model (priority: CLI > env var > config)
    model = os.getenv("OPENAI_MODEL")
    model_source = "environment variable"
    
    if not model:
        config_model = load_model_from_config()
        if config_model:
            model = config_model
            model_source = "config.json"
        else:
            model = None
            model_source = "not set"
    
    # Determine API key (priority: env var > auth.json for resolved provider)
    api_key = os.getenv("OPENAI_API_KEY")
    api_key_source = "environment variable"
    
    if not api_key:
        api_key = get_api_key(provider)
        if api_key:
            api_key_source = f"auth.json (provider: {provider})"
        else:
            api_key_source = "not set"
    
    # Determine endpoint/base URL (priority: CLI/OPENAI_BASE_URL > config > provider default)
    cli_endpoint = getattr(args, 'endpoint', None)
    env_endpoint = os.getenv("OPENAI_BASE_URL")
    config_endpoint = load_endpoint_from_config()
    
    endpoint = None
    endpoint_source = "not set"
    
    if cli_endpoint:
        endpoint = cli_endpoint
        endpoint_source = "CLI argument"
    elif env_endpoint:
        endpoint = env_endpoint
        endpoint_source = "environment variable"
    elif config_endpoint:
        endpoint = config_endpoint
        endpoint_source = "config.json"
    elif is_custom_provider(provider):
        endpoint_source = "required but not set (use --endpoint or set endpoint in config.json)"
    
    # Print the info
    print("Resolved Configuration:")
    print("=" * 40)
    print(f"Provider:     {provider} ({provider_source})")
    print(f"Model:        {model or '(not set)'} ({model_source})")
    print(f"API Key:      {get_masked_api_key(api_key)} ({api_key_source})")
    print(f"Endpoint:     {endpoint or '(not set)'} ({endpoint_source})")
    print("=" * 40)
    print(f"Config file:  {get_config_path()}")
    
    # Try to show auth file path too
    auth_path = get_auth_file_path()
    if auth_path.exists():
        print(f"Auth file:    {auth_path}")
    
    print()
    
    # Show source details
    if model_source == "not set":
        print("Note: Model not configured. Use --model, OPENAI_MODEL env var, or config.json")
    if api_key_source == "not set":
        print("Note: API key not configured. Use --set-api-key or OPENAI_API_KEY env var")
    if is_custom_provider(provider) and not endpoint:
        print("Note: Endpoint not configured. Use --endpoint or set endpoint in config.json")
    
    return 0


def handle_show_config() -> int:
    """Handle --show-config command.
    
    Displays the currently configured provider and model from config files.
    
    Returns:
        int: Exit code (0 for success)
    """
    # Load configured values from config.json
    provider = load_provider_from_config()
    model = load_model_from_config()
    
    print("Current Configuration:")
    print("=" * 40)
    print(f"Provider:  {provider or '(not configured)'}")
    print(f"Model:     {model or '(not configured)'}")
    print("=" * 40)
    
    return 0
