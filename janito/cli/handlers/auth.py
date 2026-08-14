"""Authentication-related CLI handlers."""

import json
import sys

from ...auth_config import (
    get_api_key,
    get_auth_file_path,
    get_auth_file_paths,
    get_default_provider,
    set_api_key,
)
from ...config_keys import get_masked_api_key
from ...general_config import load_provider_from_config


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
        f"Warning: an API key is already configured for provider '{provider}' ({get_masked_api_key(existing_key)}).",
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

    The target provider is taken from ``--provider``; when it is not given,
    the configured default provider is used (the ``provider`` value from
    config.json, or the default provider stored in auth.json). If no default
    provider is configured either, the command fails with an error.

    If an API key is already stored for the provider, the user is warned and
    prompted to approve the overwrite unless ``--force`` was given. When stdin
    is not interactive and ``--force`` was not given, the overwrite is refused
    (there is no way to ask) and the command fails with a hint.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    provider = args.provider
    if not provider:
        provider = load_provider_from_config() or get_default_provider()
        if not provider:
            print(
                "Error: no provider given and no default provider is configured",
                file=sys.stderr,
            )
            print(
                "Pass --provider <name>, or set a default provider first (janito --set provider=<name>).",
                file=sys.stderr,
            )
            return 1
        print(f"Using configured provider '{provider}'")

    force = getattr(args, "force", False)
    existing_key = get_api_key(provider)

    if existing_key and not force:
        if not sys.stdin.isatty():
            print(
                f"Error: an API key is already configured for provider "
                f"'{provider}'. Re-run with --force to overwrite it "
                f"non-interactively.",
                file=sys.stderr,
            )
            return 1
        if not _confirm_overwrite(provider, existing_key):
            print("Aborted: the existing API key was kept unchanged.")
            return 1

    success = set_api_key(provider, args.set_api_key)

    if success:
        auth_file = get_auth_file_path()
        print(f"✓ API key stored successfully for provider '{provider}'")
        print(f"  Config file: {auth_file}")
        return 0
    else:
        print("Error: Failed to store API key", file=sys.stderr)
        return 1


def handle_list_keys(args) -> int:
    """Handle --list-keys command.

    Shows the providers configured in each existing auth.json along the
    resolution chain: with ``-l`` / ``--local`` both the project-local
    ``./.janito/auth.json`` and the global ``~/.janito/auth.json`` (or the
    ``-c`` override) are listed; otherwise only the base file is shown.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from rich.console import Console
    from rich.table import Table

    auth_paths = [p for p in get_auth_file_paths() if p.exists()]

    console = Console(markup=False)

    if not auth_paths:
        print("No providers configured.")
        print(f"Config file: {get_auth_file_path()}")
        print()
        print("Use --set-api-key with --provider to add API keys:")
        print("  janito --set-api-key <key> --provider openai")
        return 0

    for auth_file in auth_paths:
        print(f"Config file: {auth_file}")
        with open(auth_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        providers = [key for key in config if key != "provider"]
        if not providers:
            print("  (no providers configured)")
            print()
            continue

        table = Table(
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Provider", style="green", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        for provider in providers:
            table.add_row(provider, "***")
        console.print(table)
        print()

    return 0
