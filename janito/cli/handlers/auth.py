"""Authentication-related CLI handlers."""

import sys

try:
    from ...auth_config import (
        get_api_key,
        get_auth_file_path,
        list_providers,
        set_api_key,
    )
    from ...general_config import get_masked_api_key
except ImportError:
    from janito.auth_config import (
        get_api_key,
        get_auth_file_path,
        list_providers,
        set_api_key,
    )
    from janito.general_config import get_masked_api_key


def _confirm_overwrite(provider: str, existing_key: str) -> bool:
    """Warn the user an API key already exists and ask to confirm overwriting.

    The prompt defaults to *not* overwriting so that an accidental Enter keeps
    the previously stored key.

    Args:
        provider: The provider whose key would be overwritten
        existing_key: The currently stored (masked for display) API key

    Returns:
        True if the user explicitly approved the overwrite, False otherwise.
    """
    print(
        f"Warning: an API key is already configured for provider '{provider}' "
        f"({get_masked_api_key(existing_key)}).",
        file=sys.stderr,
    )
    while True:
        try:
            answer = input("Overwrite the existing API key? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def handle_set_api_key(args) -> int:
    """Handle --set-api-key command.

    If an API key is already stored for the provider, the user is warned and
    prompted to approve the overwrite unless ``--force`` was given. When stdin
    is not interactive and ``--force`` was not given, the overwrite is refused
    (there is no way to ask) and the command fails with a hint.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.provider:
        print("Error: --provider is required when using --set-api-key", file=sys.stderr)
        print("Usage: janito --set-api-key <key> --provider <name>", file=sys.stderr)
        return 1

    force = getattr(args, "force", False)
    existing_key = get_api_key(args.provider)

    if existing_key and not force:
        if not sys.stdin.isatty():
            print(
                f"Error: an API key is already configured for provider "
                f"'{args.provider}'. Re-run with --force to overwrite it "
                f"non-interactively.",
                file=sys.stderr,
            )
            return 1
        if not _confirm_overwrite(args.provider, existing_key):
            print("Aborted: the existing API key was kept unchanged.")
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
