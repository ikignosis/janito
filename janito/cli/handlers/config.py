"""Configuration-related CLI handlers."""

import sys

try:
    from ...auth_config import get_api_key, set_api_key
    from ...general_config import (
        ProviderRequiredError,
        get_config_from_cli,
        get_config_path,
        get_masked_api_key,
        load_context_window_size,
        load_endpoint_from_config,
        load_model_from_config,
        load_provider_from_config,
        set_config_from_cli,
        unset_config_key_from_cli,
    )
    from ...provider_config import is_custom_provider, list_supported_providers
except ImportError:
    from janito.auth_config import get_api_key, set_api_key
    from janito.general_config import (
        ProviderRequiredError,
        get_config_from_cli,
        get_config_path,
        get_masked_api_key,
        load_context_window_size,
        load_endpoint_from_config,
        load_model_from_config,
        load_provider_from_config,
        set_config_from_cli,
        unset_config_key_from_cli,
    )
    from janito.provider_config import is_custom_provider, list_supported_providers


def handle_get_config(keys: list[str], cli_provider: str = None) -> int:
    """Handle --get command.

    Args:
        keys: List of configuration keys to retrieve
        cli_provider: Provider passed via ``--provider`` (used for
            provider-scoped keys such as ``model``)

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        if not keys:
            # No keys specified, show all config
            import json

            with open(get_config_path(), "r") as f:
                config = json.load(f)
            print(json.dumps(config, indent=2))
            return 0

        errors = False
        for key in keys:
            try:
                value = get_config_from_cli(key, cli_provider)
            except ProviderRequiredError as e:
                print(f"[ERROR] {e}", file=sys.stderr)
                errors = True
                continue
            if value is not None:
                print(value)
            else:
                print(f"[WARN] Key '{key}' not found in config", file=sys.stderr)
                errors = True

        return 1 if errors else 0
    except FileNotFoundError:
        print(f"Config file not found: {get_config_path()}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}", file=sys.stderr)
        return 1


def handle_set_config(values: list[str], cli_provider: str = None) -> int:
    """Handle --set command.

    Args:
        values: List of KEY=VALUE strings to set
        cli_provider: Provider passed via ``--provider`` (used for
            provider-scoped keys such as ``model``)

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not values:
        print("[ERROR] At least one KEY=VALUE pair required.", file=sys.stderr)
        print(
            "Usage: janito --set model=gpt-4 endpoint=https://api.example.com/v1",
            file=sys.stderr,
        )
        return 1

    errors = False
    for value_str in values:
        try:
            key, value = set_config_from_cli(value_str, cli_provider)
            print(f"[OK] Set {key}={value}")
        except ProviderRequiredError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            errors = True
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            errors = True

    return 1 if errors else 0


def handle_unset_config(keys: list[str], cli_provider: str = None) -> int:
    """Handle --unset command.

    Args:
        keys: List of configuration keys to remove
        cli_provider: Provider passed via ``--provider`` (used for
            provider-scoped keys such as ``model``)

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    if not keys:
        print("[ERROR] At least one key required.", file=sys.stderr)
        print("Usage: janito --unset model provider", file=sys.stderr)
        return 1

    errors = False
    for key in keys:
        try:
            removed = unset_config_key_from_cli(key, cli_provider)
        except ProviderRequiredError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            errors = True
            continue
        if removed:
            print(f"[OK] Removed '{key}'")
        else:
            print(f"[WARN] Key '{key}' not found in config", file=sys.stderr)
            errors = True

    return 1 if errors else 0


def handle_config_interactive() -> int:
    """Handle --config command for interactive configuration setup.

    Prompts the user for:
    - Provider name (with existing config value as default)
    - API key (with existing auth value for that provider as default, masked)
    - Max context window size (with existing config value as default, default 65536)
    - Endpoint (required only for 'custom' provider)

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Load existing values
    existing_provider = load_provider_from_config()
    existing_model = load_model_from_config(existing_provider)
    existing_context_window = load_context_window_size(existing_provider)
    existing_endpoint = load_endpoint_from_config()

    # Mask existing API key for display
    def mask_api_key(key: str) -> str:
        return get_masked_api_key(key)

    # Helper for prompting with default
    def prompt_with_default(
        prompt_text: str, default: str = None, is_password: bool = False
    ) -> str:
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
    print("  janito Interactive Configuration")
    print("=" * 50)
    print()

    # Provider name
    print("Provider Configuration")
    print("-" * 30)
    supported = list_supported_providers()
    print(f"Available providers: {', '.join(sorted(supported))}")
    print()
    provider = prompt_with_default("Enter provider name", default=existing_provider)
    if not provider:
        print("Error: Provider name is required.", file=sys.stderr)
        return 1
    provider = provider.strip().lower()
    print(f"  Using provider: {provider}")
    print()

    # Check if API key already exists for this provider in auth config
    existing_api_key = get_api_key(provider)
    if existing_api_key:
        print(
            f"  Found existing API key for '{provider}': {mask_api_key(existing_api_key)}"
        )
    else:
        print(f"  No API key found for '{provider}' in auth config")
    print()

    # API key
    print("Authentication")
    print("-" * 30)
    api_key = prompt_with_default(
        "Enter API key", default=existing_api_key, is_password=True
    )
    if not api_key:
        print("Error: API key is required.", file=sys.stderr)
        return 1
    api_key = api_key.strip()
    print(f"  API key: {mask_api_key(api_key)}")
    print()

    # Model
    print("Model")
    print("-" * 30)
    # Default to the model already configured for the selected provider.
    default_model = load_model_from_config(provider) or existing_model
    model = prompt_with_default("Enter model name", default=default_model)
    if not model:
        print("Error: Model name is required.", file=sys.stderr)
        return 1
    model = model.strip()
    print(f"  Using model: {model}")
    print()

    # Context window size
    print("Context Window")
    print("-" * 30)
    default_context = existing_context_window if existing_context_window else 65536
    context_str = prompt_with_default(
        "Enter max context window size", default=str(default_context)
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

    # Endpoint (only required for 'custom' provider)
    endpoint = None
    if is_custom_provider(provider):
        print("Endpoint (required for 'custom' provider)")
        print("-" * 30)
        # Default to the endpoint already configured for the selected provider.
        default_endpoint = load_endpoint_from_config(provider) or existing_endpoint
        endpoint = prompt_with_default(
            "Enter API endpoint URL", default=default_endpoint
        )
        if not endpoint:
            print("Error: Endpoint is required for 'custom' provider.", file=sys.stderr)
            return 1
        endpoint = endpoint.strip()
        print(f"  Using endpoint: {endpoint}")
        print()

    # Confirm changes
    print("=" * 50)
    print("Configuration Summary:")
    print("-" * 30)
    print(f"  Provider:          {provider}")
    print(f"  Model:             {model}")
    print(f"  API Key:           {mask_api_key(api_key)}")
    print(f"  Context Window:    {context_window}")
    if endpoint:
        print(f"  Endpoint:          {endpoint}")
    print("=" * 50)
    print()

    confirm = input("Save these settings? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("Configuration cancelled.")
        return 0

    # Save settings
    try:
        # Save provider to config.json
        set_config_from_cli(f"provider={provider}")
        print(f"[OK] Saved provider '{provider}' to config")

        # Save model to config.json under the provider-scoped key
        # (e.g. "openai.model") so each provider has its own default model.
        set_config_from_cli(f"model={model}", provider)
        print(f"[OK] Saved model '{model}' to config ({provider}.model)")

        # Save context window to config.json under the provider-scoped key
        # (e.g. "openai.context-window-size") so each provider has its own context window.
        set_config_from_cli(f"context-window-size={context_window}", provider)
        print(
            f"[OK] Saved context window {context_window} to config ({provider}.context-window-size)"
        )

        # Save endpoint to config.json under the provider-scoped key
        # (e.g. "custom.endpoint") so each provider has its own endpoint.
        if endpoint:
            set_config_from_cli(f"endpoint={endpoint}", provider)
            print(f"[OK] Saved endpoint to config ({provider}.endpoint)")

        # Save API key to auth.json
        if set_api_key(provider, api_key):
            print(f"[OK] Saved API key for provider '{provider}'")
        else:
            print("Error: Failed to save API key.", file=sys.stderr)
            return 1

        print()
        print("Configuration saved successfully!")
        return 0

    except Exception as e:
        print(f"Error saving configuration: {e}", file=sys.stderr)
        return 1
