#!/usr/bin/env python3
"""
OpenAI CLI - A simple command-line interface to interact with OpenAI-compatible endpoints.

This CLI uses environment variables for configuration:
- OPENAI_BASE_URL: The base URL of the OpenAI-compatible API endpoint (optional for standard OpenAI)
- OPENAI_API_KEY: The API key for authentication
- OPENAI_MODEL: The model name to use for completions

API keys can also be stored securely in ~/.janito/auth.json using the --set-api-key option.

The CLI includes function calling tools that can be used by the AI model.

Usage:
    python -m janito "Your prompt here"                    # Single prompt mode
    echo "Your prompt" | python -m janito                  # Pipe input mode
    python -m janito                                       # Interactive chat session
    python -m janito --set-api-key <key> --provider <name> # Store API key
"""

from .cli.logging_config import setup_logging
from .cli import create_parser
from .cli.setup import (
    setup_api_key_from_config,
    setup_provider_env,
    setup_endpoint_env,
    setup_model_env,
    validate_required_config,
)
from .cli.input import read_stdin_prompt
from .cli.chat import run_interactive_chat, run_single_prompt
from .cli.handlers import (
    handle_set_api_key,
    handle_list_auth,
    handle_get_config,
    handle_set_config,
    handle_unset_config,
    handle_config_interactive,
    handle_info,
    handle_show_config,
    handle_list_tools,
    handle_list_mcp,
    handle_set_secret,
    handle_get_secret,
    handle_delete_secret,
    handle_list_secrets,
    handle_install_skill,
    handle_list_skills,
    handle_uninstall_skill,
)
from .cli.handlers.onedrive import (
    handle_onedrive_auth,
    handle_onedrive_logout,
    handle_onedrive_status,
)


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
    
    # Configure logging based on --log argument
    setup_logging(args.log)
    
    # Handle batch config operations (--set, --unset, --get, secrets)
    if args.set is not None or args.unset is not None or args.get is not None or args.set_secret is not None or args.delete_secret is not None:
        exit_code = 0
        
        set_values = _flatten(args.set) if args.set is not None else None
        unset_keys = _flatten(args.unset) if args.unset is not None else None
        get_keys = _flatten(args.get) if args.get is not None else None
        set_secret_vals = _flatten(args.set_secret) if args.set_secret is not None else None
        delete_secret_keys = _flatten(args.delete_secret) if args.delete_secret is not None else None
        
        if set_values is not None:
            rc = handle_set_config(set_values)
            if rc != 0:
                exit_code = rc
        
        if unset_keys is not None:
            rc = handle_unset_config(unset_keys)
            if rc != 0:
                exit_code = rc
        
        if get_keys is not None:
            rc = handle_get_config(get_keys)
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
        return handle_show_config()
    
    # Set up provider from CLI args
    setup_provider_env(args)
    
    # Set up endpoint from CLI args or config (for custom provider)
    setup_endpoint_env(args)
    
    # Handle --get for a single key (legacy: no --set/--unset provided)
    # Note: --get without --set/--unset was handled above, but if only --get was passed
    # alone with nargs="*", it would be caught by the batch block. This path handles edge cases.
    
    # Handle interactive config setup
    if args.config:
        return handle_config_interactive()
    
    # Handle auth commands
    if args.list_auth:
        return handle_list_auth(args)
    
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
    
    # Try to load API key from config if not set in environment
    setup_api_key_from_config()
    
    # Set up model environment variable
    setup_model_env(args)
    
    # Handle info/list commands (these return early)
    if args.list_tools:
        return handle_list_tools(args)
    
    if args.list_mcp:
        return handle_list_mcp(args)
    
    # Validate required configuration
    validate_required_config()
    
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
