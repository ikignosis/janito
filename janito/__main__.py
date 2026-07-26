#!/usr/bin/env python3
"""
OpenAI CLI - A simple command-line interface to interact with OpenAI-compatible endpoints.

This CLI resolves its configuration from local files (no environment variables):
- API key:  from ~/.janito/auth.json for the active provider (--set-api-key)
- Endpoint: the provider's built-in default, or an endpoint override in
            ~/.janito/config.json (--set endpoint=...)
- Model:    --model, or the provider's configured model (--set model=...)

API keys are stored securely in ~/.janito/auth.json using the --set-api-key option.

The CLI includes function calling tools that can be used by the AI model.

Usage:
    python -m janito "Your prompt here"                    # Single prompt mode
    echo "Your prompt" | python -m janito                  # Pipe input mode
    python -m janito                                       # Interactive chat session
    python -m janito --set-api-key <key> --provider <name> # Store API key
"""


from . import privileges as _privileges_mod
from .cli import create_parser
from .cli.chat import run_interactive_chat, run_single_prompt
from .cli.handlers import (
    handle_config_interactive,
    handle_delete_secret,
    handle_get_config,
    handle_get_secret,
    handle_info,
    handle_install_skill,
    handle_list_keys,
    handle_list_mcp,
    handle_list_secrets,
    handle_list_skills,
    handle_list_tools,
    handle_set_api_key,
    handle_set_config,
    handle_set_secret,
    handle_show_config,
    handle_show_system_prompt,
    handle_uninstall_skill,
    handle_unset_config,
)
from .cli.handlers.onedrive import (
    handle_onedrive_auth,
    handle_onedrive_logout,
    handle_onedrive_status,
)
from .cli.input import read_stdin_prompt
from .cli.logging_config import setup_logging
from .cli.setup import validate_runtime_config
from .config_dir import set_config_dir
from .privileges import Privileges


def _flatten(values):
    """Flatten [['a', 'b'], ['c']] -> ['a', 'b', 'c']"""
    if not values:
        return []
    flat = []
    for item in values:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Apply the -c/--config-dir override as early as possible so that all
    # subsequent config/auth/secrets/MCP/skills reads and writes use the
    # requested directory instead of the default ~/.janito.
    set_config_dir(getattr(args, "config_dir", None))

    # Configure logging based on --log argument
    setup_logging(args.log)

    # Set up privileges from -r, -w, -x flags
    if args.read or args.write or args.exec:
        if _privileges_mod.running_privileges is None:
            _privileges_mod.running_privileges = Privileges()
        if args.read:
            _privileges_mod.running_privileges.READ = True
        if args.write:
            _privileges_mod.running_privileges.WRITE = True
        if args.exec:
            _privileges_mod.running_privileges.EXEC = True

    if _privileges_mod.running_privileges is None:
        args.full_privileges = True

    # Handle batch config operations (--set, --unset, --get, secrets)
    if (
        args.set is not None
        or args.unset is not None
        or args.get is not None
        or args.set_secret is not None
        or args.delete_secret is not None
    ):
        exit_code = 0

        set_values = _flatten(args.set) if args.set is not None else None
        unset_keys = _flatten(args.unset) if args.unset is not None else None
        get_keys = _flatten(args.get) if args.get is not None else None
        set_secret_vals = (
            _flatten(args.set_secret) if args.set_secret is not None else None
        )
        delete_secret_keys = (
            _flatten(args.delete_secret) if args.delete_secret is not None else None
        )

        # Provider used for provider-scoped config keys (e.g. model). It is
        # taken from --provider, falling back to the configured provider value.
        cli_provider = getattr(args, "provider", None)

        if set_values is not None:
            rc = handle_set_config(set_values, cli_provider)
            if rc != 0:
                exit_code = rc

        if unset_keys is not None:
            rc = handle_unset_config(unset_keys, cli_provider)
            if rc != 0:
                exit_code = rc

        if get_keys is not None:
            rc = handle_get_config(get_keys, cli_provider)
            if rc != 0:
                exit_code = rc

        if set_secret_vals is not None:
            args._set_secret_vals = set_secret_vals
            rc = handle_set_secret(args)
            if rc != 0:
                exit_code = rc

        if delete_secret_keys is not None:
            args._delete_secret_keys = delete_secret_keys
            rc = handle_delete_secret(args)
            if rc != 0:
                exit_code = rc

        return exit_code

    # Handle --info option (print config and exit)
    if args.info:
        return handle_info(args)

    # Handle --show-config option (display configured provider and model)
    if args.show_config:
        return handle_show_config(args)

    # Handle --show-system-prompt option (display resolved system prompt and exit)
    if args.show_system_prompt:
        return handle_show_system_prompt(args)

    # Handle --get for a single key (legacy: no --set/--unset provided)
    # Note: --get without --set/--unset was handled above, but if only --get was passed
    # alone with nargs="*", it would be caught by the batch block. This path handles edge cases.

    # Handle interactive config setup
    if args.config:
        return handle_config_interactive()

    # Handle auth commands
    if args.list_keys:
        return handle_list_keys(args)

    if args.set_api_key:
        return handle_set_api_key(args)

    # Handle secrets get/list/delete
    if args.list_secrets:
        return handle_list_secrets(args)

    if args.get_secret is not None:
        return handle_get_secret(args)

    # Handle OneDrive auth commands
    if args.onedrive_auth:
        return handle_onedrive_auth()

    if args.onedrive_logout:
        return handle_onedrive_logout()

    if args.onedrive_status:
        return handle_onedrive_status()

    # Handle skill commands
    if args.install_skill:
        return handle_install_skill(args.install_skill)

    if args.list_skills:
        return handle_list_skills(args)

    if args.uninstall_skill:
        return handle_uninstall_skill(args.uninstall_skill)

    # Handle info/list commands (these return early)
    if args.list_tools:
        return handle_list_tools(args)

    if args.list_mcp:
        return handle_list_mcp(args)

    # Validate that the runtime configuration (API key from auth store,
    # endpoint from provider default/config, model from --model or config)
    # can be resolved before starting a session.
    validate_runtime_config(args)

    # Web mode: skip stdin check — the server doesn't consume stdin.
    # Must come BEFORE read_stdin_prompt() to avoid blocking on non-tty
    # stdin in headless / service contexts.
    if args.web:
        try:
            from .web.backend.app import run_web
        except ImportError as e:
            # The [web] extra (fastapi / uvicorn) is not installed.
            # Fail with an actionable message instead of a raw traceback.
            import sys as _sys

            print(
                "Error: the web UI requires optional dependencies that "
                "are not installed.",
                file=_sys.stderr,
            )
            print(
                "Install them with:\n\n    pip install janito[web]\n", file=_sys.stderr
            )
            print(f"(missing module: {getattr(e, 'name', e)})", file=_sys.stderr)
            _sys.exit(1)
        run_web(args)
        return

    # Check for stdin input
    stdin_prompt = read_stdin_prompt()
    if stdin_prompt:
        args.prompt = stdin_prompt

    # Run chat or single prompt
    if args.prompt is None:
        run_interactive_chat(args)
    else:
        run_single_prompt(args)


if __name__ == "__main__":
    main()
