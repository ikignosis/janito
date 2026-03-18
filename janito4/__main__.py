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
import json
import argparse
from typing import List, Dict, Any
from .system_prompt import SYSTEM_PROMPT

# Import the send_prompt function from the new module
try:
    from .openai_client import send_prompt
except ImportError:
    # When running directly, not as a module
    from openai_client import send_prompt

# Import auth configuration handling
try:
    from .auth_config import (
        set_api_key, get_api_key, load_auth_config, 
        get_auth_file_path, list_providers
    )
except ImportError:
    from auth_config import (
        set_api_key, get_api_key, load_auth_config,
        get_auth_file_path, list_providers
    )

# Import general configuration handling
from janito4.general_config import (
    load_provider_from_config, load_model_from_config,
    get_active_provider, get_config_path,
    set_config_value, get_config_value,
    get_config_from_cli, set_config_from_cli,
    unset_config_value
)

# Import interactive shell
from .shell import InteractiveShell


def setup_api_key_from_config(debug: bool = False):
    """Load API key from auth config if environment variable is not set.
    
    Priority:
    1. Provider from config.json (highest)
    2. Default provider from auth.json
    3. Fallback to 'openai'
    
    Args:
        debug: If True, print debug messages
    """
    if not os.getenv("OPENAI_API_KEY"):
        # Try to determine which provider to use
        provider = None
        
        # 1. First check config.json for provider
        config_provider = load_provider_from_config()
        if config_provider:
            provider = config_provider
            if debug:
                print(f"[DEBUG] Provider from config.json: {provider}")
        else:
            # 2. Check auth.json for default provider
            try:
                from .auth_config import get_default_provider
            except ImportError:
                from auth_config import get_default_provider
            
            default_provider = get_default_provider()
            if default_provider:
                provider = default_provider
                if debug:
                    print(f"[DEBUG] Provider from auth.json (default): {provider}")
            else:
                # 3. Fall back to 'openai'
                provider = "openai"
                if debug:
                    print(f"[DEBUG] Using default provider: {provider}")
        
        # Try to load API key for the determined provider
        try:
            from .auth_config import get_api_key
        except ImportError:
            from auth_config import get_api_key
        
        api_key = get_api_key(provider)
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            if debug:
                print(f"[DEBUG] API key loaded from config for provider: {provider}")
            return True
        else:
            if debug:
                print(f"[DEBUG] No API key found for provider: {provider}")
    else:
        if debug:
            print(f"[DEBUG] API key already set from environment variable")
    
    return False


def get_masked_api_key(api_key: str) -> str:
    """Mask an API key to show only first and last few characters.
    
    Args:
        api_key: The API key to mask
        
    Returns:
        str: Masked API key showing first 6 and last 4 characters
    """
    if not api_key:
        return "(not set)"
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:6]}...{api_key[-4:]}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OpenAI CLI - Send prompts to OpenAI-compatible endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  OPENAI_BASE_URL    - Base URL of the OpenAI-compatible API endpoint (optional for standard OpenAI)
  OPENAI_API_KEY     - API key for authentication  
  OPENAI_MODEL       - Model name to use for completions

Configuration:
  API keys can be stored in ~/.janito/auth.json using --set-api-key
  If OPENAI_API_KEY is not set, the CLI will try to load from the auth config

Options:
  --set-api-key KEY  Set API key for the specified provider
  --provider NAME    Provider name (e.g., openai, anthropic, azure)
  --model NAME       Model name to use (overrides OPENAI_MODEL env var and config)
  --list-auth        List configured providers and keys
  --list-tools       List all available tools and their descriptions
  --debug            Enable debug output (shows configuration loading info)
  -Z, --no-system-prompt  Do not set a system prompt or pass any tools to the CLI

Examples:
  janito4 "What is the capital of France?"                    # Single prompt mode
  echo "Tell me a joke" | janito4                             # Pipe input mode
  janito4                                                     # Interactive chat mode
  janito4 --set-api-key sk-xxx --provider openai             # Store OpenAI API key
  janito4 --set-api-key xxx --provider anthropic             # Store API key for provider
  janito4 --list-auth                                        # Show configured providers
  janito4 --list-tools                                       # List available tools
  janito4 --model gpt-4 "Your prompt"                        # Use specific model
  janito4 --set model=gpt-4                                  # Set config value
  janito4 --unset model                                      # Remove config value
  janito4 --get model                                        # Get config value
  janito4 --debug                                           # Enable debug output
        """
    )
    
    parser.add_argument(
        "prompt", 
        nargs="?", 
        help="The prompt to send to the AI (if not provided, starts interactive chat)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (shows model and backend info)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows configuration loading info)"
    )
    
    parser.add_argument(
        "-Z", "--no-system-prompt",
        action="store_true",
        help="Do not set a system prompt (send user prompt directly)"
    )
    
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools and exit"
    )
    
    parser.add_argument(
        "--set-api-key",
        metavar="KEY",
        help="Set API key for the specified provider (requires --provider)"
    )
    
    parser.add_argument(
        "--model",
        metavar="NAME",
        help="Model name to use for completions (overrides OPENAI_MODEL env var and config)"
    )
    
    parser.add_argument(
        "--provider",
        metavar="NAME",
        help="Provider name (e.g., openai, anthropic, azure)"
    )
    

    
    parser.add_argument(
        "--list-auth",
        action="store_true",
        help="List configured authentication providers"
    )
    
    parser.add_argument(
        "--set",
        metavar="KEY=VALUE",
        help="Set a config key-value pair in ~/.janito/config.json (e.g., --set model=gpt-4)"
    )
    
    parser.add_argument(
        "--unset",
        metavar="KEY",
        help="Remove a config key from ~/.janito/config.json (e.g., --unset model)"
    )
    
    parser.add_argument(
        "--get",
        metavar="KEY",
        help="Get a config value from ~/.janito/config.json"
    )
    
    args = parser.parse_args()
    
    # Handle --get option
    if args.get:
        try:
            value = get_config_from_cli(args.get)
            if value is not None:
                print(value)
            else:
                print(f"Key '{args.get}' not found in config", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print(f"Config file not found: {get_config_path()}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle --set option
    if args.set:
        try:
            key, value = set_config_from_cli(args.set)
            print(f"[OK] Set {key}={value} in {get_config_path()}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Usage: janito4 --set model=gpt-4", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle --unset option
    if args.unset:
        if unset_config_value(args.unset):
            print(f"[OK] Removed '{args.unset}' from {get_config_path()}")
        else:
            print(f"Key '{args.unset}' not found in config", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle --list-auth option
    if args.list_auth:
        providers = list_providers()
        auth_file = get_auth_file_path()
        
        print("Configured Authentication Providers:")
        print("=" * 40)
        print(f"Config file: {auth_file}")
        print()
        
        if not providers:
            print("No providers configured.")
            print("\nUse --set-api-key with --provider to add API keys:")
            print("  janito4 --set-api-key <key> --provider openai")
        else:
            for provider in providers:
                print(f"  {provider}: ***")
        
        return
    
    # Handle --set-api-key option
    if args.set_api_key:
        if not args.provider:
            print("Error: --provider is required when using --set-api-key", file=sys.stderr)
            print("Usage: janito4 --set-api-key <key> --provider <name>", file=sys.stderr)
            sys.exit(1)
        
        success = set_api_key(args.provider, args.set_api_key)
        
        if success:
            auth_file = get_auth_file_path()
            print(f"✓ API key stored successfully for provider '{args.provider}'")
            print(f"  Config file: {auth_file}")
            
            # If this is the openai provider, also set it for current session
            if args.provider == "openai":
                os.environ["OPENAI_API_KEY"] = args.set_api_key
                print(f"  API key also set for current session")
        else:
            print("Error: Failed to store API key", file=sys.stderr)
            sys.exit(1)
        
        return
    
    # Try to load API key from config if not set in environment
    setup_api_key_from_config(debug=args.debug)
    
    # Handle model selection with priority: CLI arg > env var > config
    # 1. First, check if --model was passed on command line (highest priority)
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
        if args.debug:
            print(f"[DEBUG] Model from CLI argument: {args.model}")
    # 2. Then check environment variable
    elif not os.getenv("OPENAI_MODEL"):
        # 3. Finally, check config file
        config_model = load_model_from_config()
        if config_model:
            os.environ["OPENAI_MODEL"] = config_model
            if args.debug:
                print(f"[DEBUG] Model from config file: {config_model}")
        else:
            if args.debug:
                print(f"[DEBUG] No model configured (will fail validation)")
    else:
        if args.debug:
            print(f"[DEBUG] Model from environment variable: {os.getenv('OPENAI_MODEL')}")
    
    # Validate required environment variables at startup
    missing_vars = []
    if not os.getenv("OPENAI_API_KEY"):
        missing_vars.append("OPENAI_API_KEY")
    if not os.getenv("OPENAI_MODEL"):
        missing_vars.append("OPENAI_MODEL")
    # Note: OPENAI_BASE_URL is optional for standard OpenAI, so we don't require it
    
    if missing_vars:
        print(f"Error: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set these environment variables before running the CLI.", file=sys.stderr)
        print("\nAlternatively, you can store your API key using:", file=sys.stderr)
        print(f"  janito4 --set-api-key <your-key> --provider openai", file=sys.stderr)
        sys.exit(1)
    
    # Handle --list-tools option
    if args.list_tools:
        try:
            from .tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
        except ImportError:
            from tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
        
        schemas = get_all_tool_schemas()
        permissions = get_all_tool_permissions()
        
        print("Available Tools:")
        print("=" * 60)
        
        # Group tools by category based on name prefixes
        categories = {
            "File Operations": [],
            "System Operations": [],
            "Other": []
        }
        
        for schema in schemas:
            func_info = schema['function']
            name = func_info['name']
            perms = permissions.get(name, "")
            
            # Get parameter names only
            params = func_info['parameters']['properties']
            param_names = list(params.keys())
            
            tool_info = {
                'name': name,
                'permissions': perms,
                'params': param_names
            }
            
            if name.startswith(('Create', 'Delete', 'List', 'Read', 'Remove', 'Replace', 'Search')):
                categories["File Operations"].append(tool_info)
            elif name.startswith(('Get', 'Run')):
                categories["System Operations"].append(tool_info)
            else:
                categories["Other"].append(tool_info)
        
        # Display tools by category
        for category, tools_list in categories.items():
            if tools_list:
                print(f"\n{category}:")
                print("-" * 40)
                
                for tool in sorted(tools_list, key=lambda x: x['name']):
                    perms_str = f" [{tool['permissions']}]" if tool['permissions'] else ""
                    params_str = f" ({', '.join(tool['params'])})" if tool['params'] else " (no params)"
                    print(f"  {tool['name']}{perms_str}{params_str}")
        
        print(f"\nTotal: {len(schemas)} tools")
        print("\nPermission codes: r=read, w=write, x=execute")
        return
    
    # Check if stdin is not a tty (piped input)
    if args.prompt is None and not sys.stdin.isatty():
        # Read prompt from stdin
        try:
            prompt = sys.stdin.read().strip()
            if not prompt:
                print("Error: Empty prompt provided via stdin.", file=sys.stderr)
                sys.exit(1)
            args.prompt = prompt
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
    
    # Handle chat mode (when no prompt is provided)
    if args.prompt is None:
        
        # Get model name for the prompt (already validated at startup)
        model = os.getenv("OPENAI_MODEL")
        
        print("Starting interactive chat session. Type '/exit' to end the session, 'restart' to clear conversation history.")
        print("Special commands:")
        print("  !<command>       - Execute shell command directly (e.g., !dir, !git status)")
        print("  /config        - Show current provider, base URL, and masked API key")
        print("Key bindings: F2 = restart conversation, F12 = Do It (auto-execute)")
        
        # Initialize and run the interactive shell
        shell = InteractiveShell(model=model)
        shell.initialize_history(system_prompt=None if args.no_system_prompt else SYSTEM_PROMPT)
        shell.run(
            send_prompt_func=send_prompt,
            verbose=args.verbose,
            no_tools=args.no_system_prompt
        )
        
        return
    
    # Handle single prompt mode
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


if __name__ == "__main__":
    main()