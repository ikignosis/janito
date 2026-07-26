"""Authentication-related CLI handlers."""

import sys

try:
    from ...auth_config import get_auth_file_path, list_providers, set_api_key
except ImportError:
    from janito.auth_config import get_auth_file_path, list_providers, set_api_key


def handle_set_api_key(args) -> int:
    """Handle --set-api-key command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.provider:
        print("Error: --provider is required when using --set-api-key", file=sys.stderr)
        print("Usage: janito --set-api-key <key> --provider <name>", file=sys.stderr)
        return 1

    success = set_api_key(args.provider, args.set_api_key)

    if success:
        auth_file = get_auth_file_path()
        print(f"✓ API key stored successfully for provider '{args.provider}'")
        print(f"  Config file: {auth_file}")
        return 0
    else:
        print("Error: Failed to store API key", file=sys.stderr)
        return 1


def handle_list_keys(args) -> int:
    """Handle --list-keys command.

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
        print("  janito --set-api-key <key> --provider openai")
    else:
        for provider in providers:
            print(f"  {provider}: ***")

    return 0
