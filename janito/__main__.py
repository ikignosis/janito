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


import importlib.util
import sys

from . import privileges as _privileges_mod
from .cli import create_parser
from .cli.chat import print_version_banner, run_interactive_chat, run_single_prompt
from .cli.handlers import (
    handle_config_interactive,
    handle_delete_secret,
    handle_get_config,
    handle_get_secret,
    handle_info,
    handle_install_plugin,
    handle_install_skill,
    handle_list_keys,
    handle_list_mcp,
    handle_list_plugins,
    handle_list_secrets,
    handle_list_skills,
    handle_list_tools,
    handle_set_api_key,
    handle_set_config,
    handle_set_secret,
    handle_show_config,
    handle_show_providers,
    handle_show_system_prompt,
    handle_uninstall_plugin,
    handle_uninstall_skill,
    handle_unset_config,
)
from .cli.handlers.variants import handle_create_variant, handle_delete_variant
from .cli.input import read_stdin_prompt
from .cli.logging_config import setup_logging
from .cli.setup import validate_runtime_config
from .config_dir import set_config_dir, set_local_config_mode
from .privileges import Privileges
from .provider_validation import validate_provider_name


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


def _track_rc(exit_code: int, new_rc: int) -> int:
    """Return the first non-zero exit code seen so far."""
    return exit_code if exit_code != 0 else new_rc


def _setup_runtime(args) -> int | None:
    """Apply early CLI overrides (config dir, local mode, logging, provider, privileges)."""
    set_config_dir(getattr(args, "config_dir", None))
    set_local_config_mode(getattr(args, "local", False))
    setup_logging(args.log)

    # --no-tools: stop loading non-skill tools (skill tools stay enabled).
    # Applied before any registry access so the lazy discovery in
    # tools_registry.ensure_initialized() never runs discover_toolsets()
    # for the autoload toolsets.
    if getattr(args, "no_tools", False):
        from .tooling.tools_registry import disable_tools_loading

        disable_tools_loading()

    # Whenever --provider <name> is used, verify it is a supported provider
    # (i.e. one that maps to a built-in provider config). Normalize it to
    # its canonical casing so every downstream consumer (config scoping,
    # runtime resolution, auth store) uses a consistent provider name.
    if getattr(args, "provider", None):
        try:
            args.provider = validate_provider_name(args.provider)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    _setup_privileges(args)
    return None


def _setup_privileges(args) -> None:
    """Configure privilege flags from -r, -w, -x CLI flags."""
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


def _has_batch_config_ops(args) -> bool:
    """Return True when any batch config operation flag was passed."""
    return any(
        flag is not None
        for flag in (
            args.set,
            args.unset,
            args.get,
            args.set_secret,
            args.delete_secret,
        )
    )


def _handle_batch_config(args) -> int | None:
    """Handle batch config operations (--set, --unset, --get, secrets)."""
    if not _has_batch_config_ops(args):
        return None

    exit_code = 0
    # Provider used for provider-scoped config keys (e.g. model). It is
    # taken from --provider, falling back to the configured provider value.
    cli_provider = getattr(args, "provider", None)

    if args.set is not None:
        exit_code = _track_rc(
            exit_code, handle_set_config(_flatten(args.set), cli_provider)
        )
    if args.unset is not None:
        exit_code = _track_rc(
            exit_code, handle_unset_config(_flatten(args.unset), cli_provider)
        )
    if args.get is not None:
        exit_code = _track_rc(
            exit_code, handle_get_config(_flatten(args.get), cli_provider)
        )
    if args.set_secret is not None:
        exit_code = _track_rc(exit_code, handle_set_secret(_flatten(args.set_secret)))
    if args.delete_secret is not None:
        exit_code = _track_rc(
            exit_code, handle_delete_secret(_flatten(args.delete_secret))
        )

    return exit_code


def _dispatch_flag_command(args) -> int | None:
    """Run the single flag-driven command handler, if any was requested."""
    handlers = [
        (args.info, lambda: handle_info(args)),
        (args.show_config, lambda: handle_show_config(args)),
        (args.show_system_prompt, lambda: handle_show_system_prompt(args)),
        (args.config, lambda: handle_config_interactive()),
        (args.list_keys, lambda: handle_list_keys(args)),
        (args.show_providers, lambda: handle_show_providers(args)),
        (args.set_api_key, lambda: handle_set_api_key(args)),
        (args.list_secrets, lambda: handle_list_secrets(args)),
        (args.get_secret is not None, lambda: handle_get_secret(args)),
        (args.install_skill, lambda: handle_install_skill(args.install_skill)),
        (args.list_skills, lambda: handle_list_skills(args)),
        (args.uninstall_skill, lambda: handle_uninstall_skill(args.uninstall_skill)),
        (args.install_plugin, lambda: handle_install_plugin(args.install_plugin)),
        (args.uninstall_plugin, lambda: handle_uninstall_plugin(args.uninstall_plugin)),
        (args.list_tools, lambda: handle_list_tools(args)),
        (args.list_mcp, lambda: handle_list_mcp(args)),
        (args.list_plugins, lambda: handle_list_plugins(args)),
        (args.create_variant, lambda: handle_create_variant(args.create_variant)),
        (args.delete_variant, lambda: handle_delete_variant(args.delete_variant)),
    ]
    for enabled, handler in handlers:
        if enabled:
            return handler()
    return None


def _run_web(args) -> int:
    """Run the web UI server, failing with a hint when extras are missing."""
    # The [web] extra (fastapi / uvicorn) is optional, so check its
    # availability explicitly instead of a defensive try/except
    # ImportError fallback, and fail with an actionable message.
    if (
        importlib.util.find_spec("fastapi") is None
        or importlib.util.find_spec("uvicorn") is None
    ):
        print(
            "Error: the web UI requires optional dependencies that "
            "are not installed.",
            file=sys.stderr,
        )
        print("Install them with:\n\n    pip install janito[web]\n", file=sys.stderr)
        return 1

    from .web.backend.app import run_web

    run_web(args)
    return 0


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Apply the -c/--config-dir override, logging, provider normalization and
    # privilege flags as early as possible.
    exit_code = _setup_runtime(args)
    if exit_code is not None:
        return exit_code

    # Handle batch config operations (--set, --unset, --get, secrets)
    exit_code = _handle_batch_config(args)
    if exit_code is not None:
        return exit_code

    # Load plugins before any registry/shell access so plugin tools,
    # commands and system-prompt sections are registered for the session.
    # Runs after _setup_runtime so privileges are already applied.
    #
    # - Plugins installed in ~/.janito/plugins are autoloaded unless
    #   --no-plugins is passed (they are independent of --no-tools).
    # - Plugins explicitly requested with --plugin DIR are always loaded.
    if getattr(args, "plugin", None) or not getattr(args, "no_plugins", False):
        from .plugin_manager import load_installed_plugins, load_plugins

        # Show the version banner before any plugin loading messages so the
        # session identity is visible first.
        print_version_banner()

        if not getattr(args, "no_plugins", False):
            load_installed_plugins()
        if getattr(args, "plugin", None):
            load_plugins(args.plugin)

    # Handle single flag-driven commands (--info, --config, --list-*, ...)
    exit_code = _dispatch_flag_command(args)
    if exit_code is not None:
        return exit_code

    # Validate that the runtime configuration (API key from auth store,
    # endpoint from provider default/config, model from --model or config)
    # can be resolved before starting a session.
    validate_runtime_config(args)

    # Web mode: skip stdin check — the server doesn't consume stdin.
    # Must come BEFORE read_stdin_prompt() to avoid blocking on non-tty
    # stdin in headless / service contexts.
    if args.web:
        return _run_web(args)

    # Check for stdin input
    stdin_prompt = read_stdin_prompt()
    if stdin_prompt:
        args.prompt = stdin_prompt

    # Run chat or single prompt
    if args.prompt is None:
        run_interactive_chat(args)
    else:
        run_single_prompt(args)
    return None


if __name__ == "__main__":
    # Propagate the exit code returned by main() (e.g. 1 for aborted config
    # changes like setting an API type whose required package is missing) so
    # scripts and CI can observe failures.
    sys.exit(main())
