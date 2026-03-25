"""
CLI setup functions for configuring environment variables from args/config.
"""

import os
import sys

from ..general_config import (
    load_model_from_config,
    get_active_provider,
)
from ..auth_config import get_api_key


def setup_api_key_from_config():
    """Load API key from auth config if environment variable is not set.
    
    Priority (handled by get_active_provider):
    1. JANITO_PROVIDER environment variable (from --provider CLI arg)
    2. Provider from config.json
    3. Default provider from auth.json
    4. Fallback to 'openai'
    """
    if not os.getenv("OPENAI_API_KEY"):
        provider = get_active_provider()
        api_key = get_api_key(provider)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            return True
    
    return False


def setup_provider_env(args):
    """Set up provider environment variable from CLI args.
    
    Args:
        args: Parsed command line arguments
    """
    if args.provider:
        os.environ["JANITO_PROVIDER"] = args.provider


def setup_endpoint_env(args):
    """Set up endpoint environment variable from CLI args or config.
    
    For 'custom' provider, endpoint is required.
    For other providers, endpoint from CLI overrides the provider's default base URL.
    
    Args:
        args: Parsed command line arguments
    """
    # First check if --endpoint was passed on command line
    if args.endpoint:
        os.environ["OPENAI_BASE_URL"] = args.endpoint
    # For custom provider, also check config if no CLI endpoint provided
    elif args.provider and args.provider.lower() == "custom":
        if not os.getenv("OPENAI_BASE_URL"):
            from ..general_config import load_endpoint_from_config
            config_endpoint = load_endpoint_from_config()
            if config_endpoint:
                os.environ["OPENAI_BASE_URL"] = config_endpoint


def setup_model_env(args):
    """Set up model environment variable with priority: CLI > env > config.
    
    Args:
        args: Parsed command line arguments
    """
    # 1. First, check if --model was passed on command line (highest priority)
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    # 2. Then check environment variable
    elif not os.getenv("OPENAI_MODEL"):
        # 3. Finally, check config file
        config_model = load_model_from_config()
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
    provider = os.getenv("JANITO_PROVIDER")
    if provider and provider.lower() == "custom":
        if not os.getenv("OPENAI_BASE_URL"):
            missing_vars.append("OPENAI_BASE_URL (required for 'custom' provider)")
    
    if missing_vars:
        print(f"Error: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these environment variables before running the CLI.", file=sys.stderr)
        print("\nFor 'custom' provider, use --endpoint:", file=sys.stderr)
        print(f"  janito4 --provider custom --endpoint https://api.example.com/v1", file=sys.stderr)
        print("\nOr set the endpoint in config.json:", file=sys.stderr)
        print(f"  janito4 --set endpoint=https://api.example.com/v1", file=sys.stderr)
        sys.exit(1)
