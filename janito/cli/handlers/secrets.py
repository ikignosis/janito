"""Secrets-related CLI handlers."""

import json
import sys

from ...secrets_config import (
    delete_secret,
    get_secret,
    get_secrets_file_path,
    get_secrets_file_paths,
    list_secrets,
    set_secret,
)


def handle_set_secret(args) -> int:
    """Handle --set-secret command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    values = getattr(args, "_set_secret_vals", None) or args.set_secret

    if not values:
        print("[ERROR] At least one KEY=VALUE pair required.", file=sys.stderr)
        print(
            "Usage: janito --set-secret key=value other_key=other_value",
            file=sys.stderr,
        )
        return 1

    errors = False
    for item in values:
        if "=" not in item:
            print(
                f"[ERROR] Invalid format '{item}': requires key=value", file=sys.stderr
            )
            errors = True
            continue

        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            print("[ERROR] Secret key cannot be empty", file=sys.stderr)
            errors = True
            continue

        success = set_secret(key, value)

        if success:
            print(f"[OK] Stored secret '{key}'")
        else:
            print(f"[ERROR] Failed to store secret '{key}'", file=sys.stderr)
            errors = True

    return 1 if errors else 0


def handle_get_secret(args) -> int:
    """Handle --get-secret command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Handle both batch (from __main__ with flattened values) and standalone usage
    if (
        getattr(args, "_set_secret_vals", None) is not None
        or getattr(args, "_delete_secret_keys", None) is not None
    ):
        # Called via batch mode but this handler was invoked — should not happen normally
        pass

    keys = args.get_secret
    if keys is None:
        keys_flat = []
    elif isinstance(keys[0], list):
        # Flatten nested list from action="append"
        keys_flat = []
        for item in keys:
            keys_flat.extend(item if isinstance(item, list) else [item])
    else:
        keys_flat = keys

    if not keys_flat:
        # No keys specified, show all secrets
        secrets = list_secrets()

        import json

        print(json.dumps(secrets, indent=2))
        return 0

    errors = False
    for key in keys_flat:
        key = str(key).strip()

        if not key:
            print("[ERROR] Secret key cannot be empty", file=sys.stderr)
            errors = True
            continue

        value = get_secret(key)

        if value is not None:
            print(value)
        else:
            print(f"[WARN] Secret '{key}' not found", file=sys.stderr)
            errors = True

    return 1 if errors else 0


def handle_delete_secret(args) -> int:
    """Handle --delete-secret command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    values = getattr(args, "_delete_secret_keys", None) or args.delete_secret

    if not values:
        print("[ERROR] At least one key required.", file=sys.stderr)
        print("Usage: janito --delete-secret key1 key2", file=sys.stderr)
        return 1

    errors = False
    for key in values:
        key = key.strip()

        if not key:
            print("[ERROR] Secret key cannot be empty", file=sys.stderr)
            errors = True
            continue

        if delete_secret(key):
            print(f"[OK] Deleted secret: {key}")
        else:
            print(f"[WARN] Secret '{key}' not found", file=sys.stderr)
            errors = True

    return 1 if errors else 0


def handle_list_secrets(args) -> int:
    """Handle --list-secrets command.

    Shows the secrets stored in each existing secrets.json along the
    resolution chain: with ``-l`` / ``--local`` both the project-local
    ``./.janito/secrets.json`` and the global ``~/.janito/secrets.json`` (or
    the ``-c`` override) are listed; otherwise only the base file is shown.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    secrets_paths = [p for p in get_secrets_file_paths() if p.exists()]

    print("Configured Secrets:")
    print("=" * 40)

    if not secrets_paths:
        print("No secrets configured.")
        print(f"Config file: {get_secrets_file_path()}")
        print()
        print("Use --set-secret to add secrets:")
        print("  janito --set-secret key=value")
        return 0

    for secrets_file in secrets_paths:
        with open(secrets_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"Config file: {secrets_file}")
        if not config:
            print("  (no secrets configured)")
        else:
            for key in config:
                print(f"  {key}")
        print()

    return 0
