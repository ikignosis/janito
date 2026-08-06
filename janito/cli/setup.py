"""
CLI setup helpers.

Runtime configuration (API key, endpoint, model) is resolved on demand from the
auth store (~/.janito/auth.json) and the config file (~/.janito/config.json) --
see :func:`janito.openai_client.resolve_runtime_config`. No ``OPENAI_*``
environment variables are read or written.

These helpers only perform an early, friendly validation before a session
starts so that misconfiguration is reported with an actionable message instead
of failing deep inside the API call.
"""

import sys

from ..openai_client.completions_api import resolve_runtime_config


def validate_runtime_config(args=None) -> None:
    """Validate that the runtime configuration can be resolved.

    Resolves the API key (from the auth store), the endpoint (configured
    endpoint or the provider's built-in default) and the model (``--model`` or
    the provider's configured model). If any of these is missing, prints an
    actionable error to stderr and exits.

    Args:
        args: Parsed command line arguments (optional). ``args.model`` and
            ``args.provider`` are honored when present.

    Raises:
        SystemExit: If required configuration is missing.
    """
    cli_model = getattr(args, "model", None) if args is not None else None
    cli_provider = getattr(args, "provider", None) if args is not None else None
    try:
        resolve_runtime_config(cli_model, cli_provider)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
