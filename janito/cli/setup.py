"""
CLI setup functions for configuring environment variables from args/config.
"""

import os
import sys

from ..general_config import (
    load_model_from_config,
    load_provider_from_config,
    get_active_provider,
    load_endpoint_from_config,
)
from ..auth_config import get_api_key
from ..provider_config import get_base_url_from_provider, is_custom_provider, CUSTOM_ENDPOINT_MARKER


def setup_api_key_from_config(args=None):
    """Load API key from auth config if environment variable is not set.
    
    Priority:
    1. Provider from --provider CLI argument
    2. Provider from config.json
    3. Default provider from auth.json
    4. Fallback to 'openai'
    
    Args:
        args: Parsed command line arguments (optional). If provided and
              args.provider is set, that provider is used for key lookup.
    """
    if not os.getenv("OPENAI_API_KEY"):
        # Use --provider CLI arg if available, otherwise fall back to config
        cli_provider = getattr(args, "provider", None) if args else None
        provider = cli_provider if cli_provider else get_active_provider()
        api_key = get_api_key(provider)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            return True
    
    return False


def setup_endpoint_env(args):
    """Set up endpoint environment variable from CLI args or config.
    
    Priority:
    1. --provider CLI argument: resolves the base URL from the provider map
    2. For 'custom' provider: falls back to endpoint from config.json
    3. For known providers: falls back to endpoint from config.json, then
       to the provider's built-in base URL
    4. If no --provider is given, resolves from the configured provider
       (config.json) so that ``--set endpoint=...`` works without
       repeating ``--provider`` on every invocation.
    
    Args:
        args: Parsed command line arguments
    """
    # Resolve the provider: CLI arg first, then config.json
    provider = args.provider or load_provider_from_config()
    if not provider:
        return

    base_url = get_base_url_from_provider(provider)
    if is_custom_provider(provider):
        # Custom provider: base_url is the CUSTOM_ENDPOINT marker,
        # so we need an explicit endpoint from config or env
        if not os.getenv("OPENAI_BASE_URL"):
            config_endpoint = load_endpoint_from_config(provider)
            if config_endpoint:
                os.environ["OPENAI_BASE_URL"] = config_endpoint
    elif base_url is not None:
        # Known provider: fall back to the provider's built-in base URL.
        # An already-set OPENAI_BASE_URL (from the environment or config)
        # is an explicit override and must NOT be clobbered. This matters
        # for providers like Alibaba, where some API keys (e.g. token-plan
        # "sk-sp-" keys) are only valid against a non-default endpoint;
        # overwriting the user's endpoint with the provider default causes
        # a 401 "invalid_api_key" even though the correct key is selected.
        if not os.getenv("OPENAI_BASE_URL"):
            config_endpoint = load_endpoint_from_config(provider)
            os.environ["OPENAI_BASE_URL"] = config_endpoint or base_url
    # If base_url is None (e.g. "openai"), leave OPENAI_BASE_URL unset
    # so the standard OpenAI endpoint is used


def setup_model_env(args):
    """Set up model environment variable with priority: CLI > env > config.

    The model is read from the provider-scoped config key
    (``<provider>.model``), where the provider is resolved from ``--provider``
    or the configured ``provider`` value.

    Args:
        args: Parsed command line arguments
    """
    # 1. First, check if --model was passed on command line (highest priority)
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    # 2. Then check environment variable
    elif not os.getenv("OPENAI_MODEL"):
        # 3. Finally, check config file for the active provider's model
        cli_provider = getattr(args, "provider", None)
        config_model = load_model_from_config(cli_provider)
        if config_model:
            os.environ["OPENAI_MODEL"] = config_model


def validate_required_config():
    """Validate that required environment variables are set.
    
    Raises:
        SystemExit: If required variables are missing
    """
    missing_vars = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
    if not os.getenv("OPENAI_MODEL"):
        missing_vars.append("OPENAI_MODEL")
    
    # For custom provider, validate endpoint is set
    provider = load_provider_from_config()
    if provider and provider.lower() == "custom":
        if not os.getenv("OPENAI_BASE_URL"):
            missing_vars.append("OPENAI_BASE_URL (required for 'custom' provider)")
    
    if missing_vars:
        print(f"Error: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these environment variables before running the CLI.", file=sys.stderr)
        print("\nFor 'custom' provider, set the endpoint in config.json:", file=sys.stderr)
        print(f"  janito --provider custom --set endpoint=https://api.example.com/v1", file=sys.stderr)
        sys.exit(1)
