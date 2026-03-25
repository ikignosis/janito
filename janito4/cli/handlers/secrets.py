"""Secrets-related CLI handlers."""

import sys

try:
    from ...secrets_config import (
        set_secret,
        get_secret,
        delete_secret,
        list_secrets,
        get_secrets_file_path,
    )
except ImportError:
    from janito4.secrets_config import (
        set_secret,
        get_secret,
        delete_secret,
        list_secrets,
        get_secrets_file_path,
    )


def handle_set_secret(args) -> int:
    """Handle --set-secret command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.set_secret:
        print("Error: --set-secret requires a key=value argument", file=sys.stderr)
        print("Usage: janito4 --set-secret key=value", file=sys.stderr)
        return 1
    
    # Parse key=value
    if '=' not in args.set_secret:
        print("Error: --set-secret requires key=value format", file=sys.stderr)
        print("Usage: janito4 --set-secret key=value", file=sys.stderr)
        return 1
    
    key, value = args.set_secret.split('=', 1)
    key = key.strip()
    value = value.strip()
    
    if not key:
        print("Error: Secret key cannot be empty", file=sys.stderr)
        return 1
    
    success = set_secret(key, value)
    
    if success:
        secrets_file = get_secrets_file_path()
        print(f"[OK] Secret stored successfully")
        print(f"  Key: {key}")
        print(f"  Config file: {secrets_file}")
        return 0
    else:
        print("Error: Failed to store secret", file=sys.stderr)
        return 1


def handle_get_secret(args) -> int:
    """Handle --get-secret command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.get_secret:
        print("Error: --get-secret requires a key argument", file=sys.stderr)
        print("Usage: janito4 --get-secret key", file=sys.stderr)
        return 1
    
    key = args.get_secret.strip()
    
    if not key:
        print("Error: Secret key cannot be empty", file=sys.stderr)
        return 1
    
    value = get_secret(key)
    
    if value is not None:
        print(value)
        return 0
    else:
        print(f"Secret '{key}' not found", file=sys.stderr)
        return 1


def handle_delete_secret(args) -> int:
    """Handle --delete-secret command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not args.delete_secret:
        print("Error: --delete-secret requires a key argument", file=sys.stderr)
        print("Usage: janito4 --delete-secret key", file=sys.stderr)
        return 1
    
    key = args.delete_secret.strip()
    
    if not key:
        print("Error: Secret key cannot be empty", file=sys.stderr)
        return 1
    
    if delete_secret(key):
        print(f"[OK] Secret deleted: {key}")
        return 0
    else:
        print(f"Secret '{key}' not found", file=sys.stderr)
        return 1


def handle_list_secrets(args) -> int:
    """Handle --list-secrets command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success)
    """
    secrets = list_secrets()
    secrets_file = get_secrets_file_path()
    
    print("Configured Secrets:")
    print("=" * 40)
    print(f"Config file: {secrets_file}")
    print()
    
    if not secrets:
        print("No secrets configured.")
        print()
        print("Use --set-secret to add secrets:")
        print("  janito4 --set-secret key=value")
    else:
        for key in secrets:
            print(f"  {key}")
    
    return 0
