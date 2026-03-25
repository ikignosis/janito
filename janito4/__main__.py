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
    python -m janito4 "Your prompt here"                    # Single prompt mode
    echo "Your prompt" | python -m janito4                  # Pipe input mode
    python -m janito4                                       # Interactive chat session
    python -m janito4 --set-api-key <key> --provider <name> # Store API key
"""

import os
import sys
import logging
from typing import List, Dict, Any

from .system_prompt import SYSTEM_PROMPT
from .cli import create_parser
from .cli.handlers import (
    handle_set_api_key,
    handle_list_auth,
    handle_get_config,
    handle_set_config,
    handle_unset_config,
    handle_config_interactive,
    handle_info,
    handle_list_tools,
    handle_list_mcp,
)
from .general_config import (
    load_provider_from_config,
    load_model_from_config,
    get_active_provider,
)

# Import the send_prompt function from the new module
try:
    from .openai_client import send_prompt
except ImportError:
    from openai_client import send_prompt

# Import auth configuration handling
try:
    from .auth_config import get_api_key
except ImportError:
    from auth_config import get_api_key

from .shell import InteractiveShell


def setup_logging(log_levels: str = None):
    """Configure logging based on --log argument.
    
    Args:
        log_levels: Comma-separated list of log levels (e.g., "info,debug")
                   Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    # Configure root logger
    logger = logging.getLogger()
    
    if log_levels:
        # Parse log levels from comma-separated string
        levels = [l.strip().upper() for l in log_levels.split(',')]
        
        # Set handlers for each level
        for level in levels:
            if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
                handler = logging.StreamHandler()
                handler.setLevel(getattr(logging, level))
                handler.setFormatter(logging.Formatter(
                    f'%(levelname)s: %(message)s' if level == 'INFO' 
                    else f'%(levelname)s: %(name)s: %(message)s'
                ))
                logger.addHandler(handler)
                logger.setLevel(getattr(logging, level))
    else:
        # Default: no logging output
        logger.setLevel(logging.CRITICAL + 1)


def setup_api_key_from_config():
    """Load API key from auth config if environment variable is not set.
    
    Priority (handled by get_active_provider):
    1. JANITO_PROVIDER environment variable (from --provider CLI arg)
    2. Provider from config.json
    3. Default provider from auth.json
    4. Fallback to 'openai'
    """
    if not os.getenv("OPENAI_API_KEY"):
        provider = get_active_provider()
        api_key = get_api_key(provider)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            return True
    
    return False


def setup_provider_env(args):
    """Set up provider environment variable from CLI args.
    
    Args:
        args: Parsed command line arguments
    """
    if args.provider:
        os.environ["JANITO_PROVIDER"] = args.provider


def setup_endpoint_env(args):
    """Set up endpoint environment variable from CLI args or config.
    
    For 'custom' provider, endpoint is required.
    For other providers, endpoint from CLI overrides the provider's default base URL.
    
    Args:
        args: Parsed command line arguments
    """
    # First check if --endpoint was passed on command line
    if args.endpoint:
        os.environ["OPENAI_BASE_URL"] = args.endpoint
    # For custom provider, also check config if no CLI endpoint provided
    elif args.provider and args.provider.lower() == "custom":
        if not os.getenv("OPENAI_BASE_URL"):
            from .general_config import load_endpoint_from_config
            config_endpoint = load_endpoint_from_config()
            if config_endpoint:
                os.environ["OPENAI_BASE_URL"] = config_endpoint


def setup_model_env(args):
    """Set up model environment variable with priority: CLI > env > config.
    
    Args:
        args: Parsed command line arguments
    """
    # 1. First, check if --model was passed on command line (highest priority)
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    # 2. Then check environment variable
    elif not os.getenv("OPENAI_MODEL"):
        # 3. Finally, check config file
        config_model = load_model_from_config()
        if config_model:
            os.environ["OPENAI_MODEL"] = config_model


def validate_required_config():
    """Validate that required environment variables are set.
    
    Raises:
        SystemExit: If required variables are missing
    """
    missing_vars = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
    if not os.getenv("OPENAI_MODEL"):
        missing_vars.append("OPENAI_MODEL")
    
    # For custom provider, validate endpoint is set
    provider = os.getenv("JANITO_PROVIDER")
    if provider and provider.lower() == "custom":
        if not os.getenv("OPENAI_BASE_URL"):
            missing_vars.append("OPENAI_BASE_URL (required for 'custom' provider)")
    
    if missing_vars:
        print(f"Error: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these environment variables before running the CLI.", file=sys.stderr)
        print("\nFor 'custom' provider, use --endpoint:", file=sys.stderr)
        print(f"  janito4 --provider custom --endpoint https://api.example.com/v1", file=sys.stderr)
        print("\nOr set the endpoint in config.json:", file=sys.stderr)
        print(f"  janito4 --set endpoint=https://api.example.com/v1", file=sys.stderr)
        sys.exit(1)


def read_stdin_prompt():
    """Read prompt from stdin if available.
    
    Returns:
        str or None: The prompt from stdin, or None if not available
    """
    if not sys.stdin.isatty():
        try:
            prompt = sys.stdin.read().strip()
            if prompt:
                return prompt
            else:
                print("Error: Empty prompt provided via stdin.", file=sys.stderr)
                sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
    return None


def run_interactive_chat(args):
    """Run the interactive chat session.
    
    Args:
        args: Parsed command line arguments
    """
    model = os.getenv("OPENAI_MODEL")
    print("Starting interactive chat session. Type '/exit' or CTRL-D to end the session")
    
    shell = InteractiveShell(model=model, no_history=args.no_history)
    shell.initialize_history(system_prompt=None if args.no_system_prompt else SYSTEM_PROMPT)
    shell.run(
        send_prompt_func=send_prompt,
        verbose=args.verbose,
        no_tools=args.no_system_prompt
    )


def run_single_prompt(args):
    """Run a single prompt.
    
    Args:
        args: Parsed command line arguments
    """
    prompt = args.prompt
    
    if not prompt:
        print("Error: Empty prompt provided.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize messages history (with or without system prompt based on -Z flag)
    if args.no_system_prompt:
        messages_history = []
        tools_to_use = []
    else:
        messages_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        tools_to_use = None

    try:
        send_prompt(prompt, verbose=args.verbose, previous_messages=messages_history, tools=tools_to_use)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging based on --log argument
    setup_logging(args.log)
    
    # Handle --info option (print config and exit)
    if args.info:
        return handle_info(args)
    
    # Set up provider from CLI args
    setup_provider_env(args)
    
    # Set up endpoint from CLI args or config (for custom provider)
    setup_endpoint_env(args)
    
    # Handle config commands (these return early)
    if args.get:
        return handle_get_config(args.get)
    
    if args.set:
        return handle_set_config(args.set)
    
    if args.unset:
        return handle_unset_config(args.unset)
    
    if args.config:
        return handle_config_interactive()
    
    # Handle auth commands
    if args.list_auth:
        return handle_list_auth(args)
    
    if args.set_api_key:
        return handle_set_api_key(args)
    
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
