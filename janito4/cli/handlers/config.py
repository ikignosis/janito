"""Configuration-related CLI handlers."""

import sys
import json

try:
    from ...general_config import (
        get_config_path,
        get_config_from_cli,
        set_config_from_cli,
        unset_config_value,
        load_provider_from_config,
        load_context_window_size,
    )
    from ...auth_config import (
        get_api_key,
        set_api_key,
    )
except ImportError:
    from janito4.general_config import (
        get_config_path,
        get_config_from_cli,
        set_config_from_cli,
        unset_config_value,
        load_provider_from_config,
        load_context_window_size,
    )
    from janito4.auth_config import (
        get_api_key,
        set_api_key,
    )


def handle_get_config(key: str) -> int:
    """Handle --get command.
    
    Args:
        key: Configuration key to retrieve
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        value = get_config_from_cli(key)
        if value is not None:
            print(value)
            return 0
        else:
            print(f"Key '{key}' not found in config", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print(f"Config file not found: {get_config_path()}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}", file=sys.stderr)
        return 1


def handle_set_config(value_str: str) -> int:
    """Handle --set command.
    
    Args:
        value_str: Key=value string to set
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        key, value = set_config_from_cli(value_str)
        print(f"[OK] Set {key}={value} in {get_config_path()}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Usage: janito4 --set model=gpt-4", file=sys.stderr)
        return 1


def handle_unset_config(key: str) -> int:
    """Handle --unset command.
    
    Args:
        key: Configuration key to remove
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if unset_config_value(key):
        print(f"[OK] Removed '{key}' from {get_config_path()}")
        return 0
    else:
        print(f"Key '{key}' not found in config", file=sys.stderr)
        return 1


def handle_config_interactive() -> int:
    """Handle --config command for interactive configuration setup.
    
    Prompts the user for:
    - Provider name (with existing config value as default)
    - API key (with existing auth value as default, masked)
    - Max context window size (with existing config value as default, default 65536)
    
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Load existing values
    existing_provider = load_provider_from_config()
    existing_api_key = get_api_key(existing_provider) if existing_provider else None
    existing_context_window = load_context_window_size()
    
    # Mask existing API key for display
    def mask_api_key(key: str) -> str:
        if not key:
            return "(not set)"
        if len(key) <= 12:
            return "***"
        return f"{key[:6]}...{key[-4:]}"
    
    # Helper for prompting with default
    def prompt_with_default(prompt_text: str, default: str = None, is_password: bool = False) -> str:
        if default:
            display_default = mask_api_key(default) if is_password else default
            prompt_text = f"{prompt_text} [{display_default}]"
        
        prompt_text = f"{prompt_text}: "
        
        while True:
            try:
                if is_password:
                    import getpass
                    value = getpass.getpass(prompt_text)
                else:
                    value = input(prompt_text)
                
                # If empty and we have a default, use it
                if not value and default is not None:
                    return default
                
                # If empty and no default required, return as-is (caller can validate)
                if not value:
                    return ""
                
                return value.strip()
            except KeyboardInterrupt:
                print("\n\nConfiguration cancelled.")
                sys.exit(0)
            except EOFError:
                print("\n\nConfiguration cancelled.")
                sys.exit(0)
    
    print("\n" + "=" * 50)
    print("  Janito4 Interactive Configuration")
    print("=" * 50)
    print()
    
    # Provider name
    print("Provider Configuration")
    print("-" * 30)
    provider = prompt_with_default(
        "Enter provider name",
        default=existing_provider
    )
    if not provider:
        print("Error: Provider name is required.", file=sys.stderr)
        return 1
    provider = provider.strip().lower()
    print(f"  Using provider: {provider}")
    print()
    
    # API key
    print("Authentication")
    print("-" * 30)
    api_key = prompt_with_default(
        "Enter API key",
        default=existing_api_key,
        is_password=True
    )
    if not api_key:
        print("Error: API key is required.", file=sys.stderr)
        return 1
    api_key = api_key.strip()
    print(f"  API key: {mask_api_key(api_key)}")
    print()
    
    # Context window size
    print("Context Window")
    print("-" * 30)
    default_context = existing_context_window if existing_context_window else 65536
    context_str = prompt_with_default(
        "Enter max context window size",
        default=str(default_context)
    )
    if not context_str:
        context_window = 65536
    else:
        try:
            context_window = int(context_str.strip())
        except ValueError:
            print("Error: Context window size must be a number.", file=sys.stderr)
            return 1
    print(f"  Using context window: {context_window}")
    print()
    
    # Confirm changes
    print("=" * 50)
    print("Configuration Summary:")
    print("-" * 30)
    print(f"  Provider:          {provider}")
    print(f"  API Key:           {mask_api_key(api_key)}")
    print(f"  Context Window:    {context_window}")
    print("=" * 50)
    print()
    
    confirm = input("Save these settings? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Configuration cancelled.")
        return 0
    
    # Save settings
    try:
        # Save provider to config.json
        set_config_from_cli(f"provider={provider}")
        print(f"[OK] Saved provider '{provider}' to config")
        
        # Save context window to config.json
        set_config_from_cli(f"context-window-size={context_window}")
        print(f"[OK] Saved context window {context_window} to config")
        
        # Save API key to auth.json
        if set_api_key(provider, api_key):
            print(f"[OK] Saved API key for provider '{provider}'")
        else:
            print(f"Error: Failed to save API key.", file=sys.stderr)
            return 1
        
        print()
        print("Configuration saved successfully!")
        return 0
        
    except Exception as e:
        print(f"Error saving configuration: {e}", file=sys.stderr)
        return 1
