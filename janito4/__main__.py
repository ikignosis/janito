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
from pathlib import Path
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

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.formatted_text import HTML


def load_provider_from_config():
    """Load provider name from ~/.janito/config.json if it exists.
    
    Returns:
        str: Provider name from config, or None if not found
        
    Raises:
        json.JSONDecodeError: If config file contains invalid JSON
    """
    config_path = Path.home() / ".janito" / "config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("provider")
    except FileNotFoundError:
        return None


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


def load_model_from_config():
    """Load model name from ~/.janito/config.json if it exists.
    
    Returns:
        str: Model name from config, or None if not found
        
    Raises:
        json.JSONDecodeError: If config file contains invalid JSON
    """
    config_path = Path.home() / ".janito" / "config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("model")
    except FileNotFoundError:
        return None


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


def get_active_provider() -> str:
    """Determine the active provider based on config and environment.
    
    Returns:
        str: The active provider name
    """
    # 1. First check config.json for provider
    config_provider = load_provider_from_config()
    if config_provider:
        return config_provider
    
    # 2. Check auth.json for default provider
    try:
        from .auth_config import get_default_provider
    except ImportError:
        from auth_config import get_default_provider
    
    default_provider = get_default_provider()
    if default_provider:
        return default_provider
    
    # 3. Fall back to 'openai'
    return "openai"


def print_info():
    """Print current configuration info (provider, base_url, masked API key)."""
    provider = get_active_provider()
    api_key = os.getenv("OPENAI_API_KEY", "")
    masked_key = get_masked_api_key(api_key)
    
    # Determine the actual base URL that will be used
    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        # Try to get base URL from provider configuration
        try:
            from .provider_config import get_base_url_from_provider
            base_url = get_base_url_from_provider(provider)
        except ImportError:
            from provider_config import get_base_url_from_provider
            base_url = get_base_url_from_provider(provider)
        
        if base_url:
            base_url_display = f"{base_url} (from provider: {provider})"
        else:
            base_url_display = "(default OpenAI URL)"
    else:
        base_url_display = base_url
    
    print()
    print("=" * 50)
    print("Configuration Info")
    print("=" * 50)
    print(f"  Provider:    {provider}")
    print(f"  Base URL:   {base_url_display}")
    print(f"  API Key:    {masked_key}")
    print("=" * 50)
    print()


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
        "--get",
        metavar="KEY",
        help="Get a config value from ~/.janito/config.json"
    )
    
    args = parser.parse_args()
    
    # Handle --get option
    if args.get:
        config_path = Path.home() / ".janito" / "config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            value = config.get(args.get)
            if value is not None:
                print(value)
            else:
                print(f"Key '{args.get}' not found in config", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print(f"Config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle --set option
    if args.set:
        if '=' not in args.set:
            print("Error: --set requires KEY=VALUE format", file=sys.stderr)
            print("Usage: janito4 --set model=gpt-4", file=sys.stderr)
            sys.exit(1)
        
        key, value = args.set.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        config_path = Path.home() / ".janito" / "config.json"
        
        # Load existing config or create new one
        config = {}
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in config file, overwriting: {e}", file=sys.stderr)
        
        # Update config
        config[key] = value
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"[OK] Set {key}={value} in {config_path}")
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
        
        print("Starting interactive chat session. Type 'exit' or 'quit' to end the session, 'restart' to clear conversation history.")
        print("Special commands:")
        print("  !<command>       - Execute shell command directly (e.g., !dir, !git status)")
        print("  /config        - Show current provider, base URL, and masked API key")
        print("Key bindings: F2 = restart conversation, F12 = Do It (auto-execute)")
        
        messages_history: List[Dict[str, Any]] = []
        restart_requested = False
        do_it_requested = False

        # Initialize messages history (with or without system prompt based on -Z flag)
        if args.no_system_prompt:
            messages_history = []
        else:
            messages_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Create key bindings
        kb = KeyBindings()
        
        @kb.add('f2')
        def restart_chat(event: KeyPressEvent) -> None:
            """Handle F2 key to restart conversation."""
            nonlocal restart_requested
            restart_requested = True
            event.app.exit(result=None)  # Exit the current prompt
        
        @kb.add('f12')
        def do_it_action(event: KeyPressEvent) -> None:
            """Handle F12 key to trigger 'Do It' auto-execution."""
            nonlocal do_it_requested
            do_it_requested = True
            event.app.exit(result="Do It")  # Return special value to trigger auto-execution
        
        session = PromptSession(history=InMemoryHistory(), key_bindings=kb)
        
        try:
            while True:
                try:
                    restart_requested = False
                    do_it_requested = False
                    # Use HTML formatting to apply dark blue background to prompt
                    prompt_text = HTML(f'<style bg="#00008b">{model} # </style>')
                    user_input = session.prompt(prompt_text)
                    
                    # Check if F12 was pressed (Do It requested)
                    if do_it_requested:
                        print("\n[Keybinding F12] 'Do It' to continue existing plan...")
                        user_input = "Do It"  # Set input to trigger the action
                    
                    # Check if F2 was pressed (restart requested)
                    if restart_requested:
                        messages_history.clear()
                        print("\n[Keybinding F2] Conversation history cleared. Starting fresh conversation.")
                        continue
                    
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    if user_input.lower() == 'restart':
                        messages_history.clear()
                        print("Conversation history cleared. Starting fresh conversation.")
                        continue
                    if user_input.lower() == '/config':
                        print_info()
                        continue
                    
                    # Handle !cmd for direct shell execution
                    if user_input.startswith('!'):
                        cmd = user_input[1:].strip()
                        if cmd:
                            print(f"[Shell] Executing: {cmd}")
                            import subprocess
                            try:
                                result = subprocess.run(
                                    cmd, 
                                    shell=True, 
                                    capture_output=True, 
                                    text=True,
                                    timeout=60
                                )
                                if result.stdout:
                                    print(result.stdout)
                                if result.stderr:
                                    print(result.stderr, file=sys.stderr)
                                print(f"[Shell] Exit code: {result.returncode}")
                            except subprocess.TimeoutExpired:
                                print("[Shell] Command timed out after 60 seconds", file=sys.stderr)
                            except Exception as e:
                                print(f"[Shell] Error: {e}", file=sys.stderr)
                        continue
                    
                    if user_input.strip():
                        tools_to_use = [] if args.no_system_prompt else None
                        response = send_prompt(user_input, verbose=args.verbose, previous_messages=messages_history, tools=tools_to_use)
                        # Add the user message and AI response to history
                        messages_history.append({"role": "user", "content": user_input})
                        if response:
                            messages_history.append({"role": "assistant", "content": response})
                except KeyboardInterrupt:
                    # Prompt user for confirmation to quit
                    try:
                        confirm = session.prompt("\nDo you want to quit the conversation? (y/n): ")
                        if confirm.lower().strip() in ['y', 'yes']:
                            raise EOFError()  # Use EOFError to trigger graceful exit
                        # If user says no, continue the loop
                        continue
                    except (KeyboardInterrupt, EOFError):
                        # If user presses Ctrl+C or Ctrl+D during confirmation, just exit
                        raise EOFError()
        except EOFError:
            pass  # Handle Ctrl+D gracefully
        print("\nChat session ended.")
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