"""Provider-variant CLI handlers (--create-variant / --delete-variant)."""

import sys

from ...auth_config import get_api_key
from ...config_variants import create_variant, delete_variant


def handle_create_variant(name: str) -> int:
    """Handle --create-variant command.

    Registers a provider variant (``<provider>-<word>``, e.g.
    ``alibaba-tokenplan``) in config.json so the name can be used as a
    provider by every other command.

    Args:
        name: The variant name to create.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not name:
        print(
            "[ERROR] A variant name is required, e.g. --create-variant alibaba-tokenplan (<provider>-<word>).",
            file=sys.stderr,
        )
        return 1

    try:
        variant = create_variant(name)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(f"[OK] Created provider variant '{variant}'")
    print()
    print("Next steps:")
    print(f"  janito --provider {variant} --set model=<name>    # per-variant model")
    print(f"  janito --provider {variant} --set endpoint=<url>  # per-variant endpoint")
    print(f"  janito --set-api-key <key> --provider {variant}   # per-variant API key")
    print(
        f"  janito --set provider={variant}                   # use as the default provider"
    )
    print()
    print(
        f"The variant inherits its base provider's built-in defaults and keeps its "
        f"own configuration under '{variant}.*'."
    )
    return 0


def handle_delete_variant(name: str) -> int:
    """Handle --delete-variant command.

    Deletes a provider variant and its per-variant configuration (model,
    endpoint, API type, tokens, reasoning level, responses-in-server) and
    API key.

    Args:
        name: The variant name to delete.

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not name:
        print(
            "[ERROR] A variant name is required, e.g. --delete-variant alibaba-tokenplan.",
            file=sys.stderr,
        )
        return 1

    had_key = bool(get_api_key(name))
    try:
        removed = delete_variant(name)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if not removed:
        print(
            f"[WARN] Provider variant '{name}' is not registered.",
            file=sys.stderr,
        )
        return 1

    if had_key:
        print(f"[OK] Deleted provider variant '{name}' (config and API key removed)")
    else:
        print(
            f"[OK] Deleted provider variant '{name}' (config removed; no API key was stored)"
        )
    return 0
