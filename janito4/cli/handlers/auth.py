"""Authentication-related CLI handlers."""

import os
import sys

try:
    from ...auth_config import set_api_key, get_api_key, list_providers, get_auth_file_path
except ImportError:
    from janito4.auth_config import set_api_key, get_api_key, list_providers, get_auth_file_path


def handle_set_api_key(args) -> int:
    """Handle --set-api-key command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.provider:
        print("Error: --provider is required when using --set-api-key", file=sys.stderr)
        print("Usage: janito4 --set-api-key <key> --provider <name>", file=sys.stderr)
        return 1
    
    success = set_api_key(args.provider, args.set_api_key)
    
    if success:
        auth_file = get_auth_file_path()
        print(f"✓ API key stored successfully for provider '{args.provider}'")
        print(f"  Config file: {auth_file}")
        
        # If this is the openai provider, also set it for current session
        if args.provider == "openai":
            os.environ["OPENAI_API_KEY"] = args.set_api_key
            print(f"  API key also set for current session")
        
        return 0
    else:
        print("Error: Failed to store API key", file=sys.stderr)
        return 1


def handle_list_auth(args) -> int:
    """Handle --list-auth command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success)
    """
    providers = list_providers()
    auth_file = get_auth_file_path()
    
    print("Configured Authentication Providers:")
    print("=" * 40)
    print(f"Config file: {auth_file}")
    print()
    
    if not providers:
        print("No providers configured.")
        print("\nUse --set-api-key with --provider to add API keys:")
        print("  janito4 --set-api-key <key> --provider openai")
    else:
        for provider in providers:
            print(f"  {provider}: ***")
    
    return 0
