"""Configuration-related CLI handlers."""

import sys

import questionary

from ...auth_config import get_api_key, set_api_key
from ...general_config import (
    ProviderRequiredError,
    get_config_from_cli,
    get_config_path,
    get_config_paths,
    get_masked_api_key,
    load_config,
    load_endpoint_from_config,
    load_max_output_tokens,
    load_model_from_config,
    load_provider_from_config,
    set_config_from_cli,
    unset_config_key_from_cli,
)
from ...provider_config import is_custom_provider, list_supported_providers


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
        import json

        if not keys:
            # No keys specified, show the resolved (merged) config: with
            # -l/--local this reflects local values overlaid on the global
            # ones (see janito.general_config.load_config).
            if not any(path.exists() for path in get_config_paths()):
                raise FileNotFoundError(get_config_path())
            print(json.dumps(load_config(), indent=2))
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


def _prompt_with_default(
    prompt_text: str, default: str = None, is_password: bool = False
) -> str:
    """Prompt the user for input, offering ``default`` when the input is empty."""
    if default:
        display_default = get_masked_api_key(default) if is_password else default
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


def _prompt_provider(existing_provider: str | None) -> str | None:
    """Prompt for the provider via a questionary select; returns None to abort."""
    print("Provider Configuration")
    print("-" * 30)
    supported = sorted(list_supported_providers())
    # Pre-select the currently configured provider when it is one of the
    # supported choices (a hand-edited config may contain an unknown name).
    default = existing_provider if existing_provider in supported else None
    try:
        provider = questionary.select(
            "Select a provider",
            choices=supported,
            default=default,
        ).ask()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(0)
    if not provider:
        print("Error: Provider name is required.", file=sys.stderr)
        return None
    print(f"  Using provider: {provider}")
    print()
    return provider


def _prompt_api_key(provider: str) -> str | None:
    """Prompt for the API key; returns None to abort."""
    # Check if API key already exists for this provider in auth config
    existing_api_key = get_api_key(provider)
    if existing_api_key:
        print(
            f"  Found existing API key for '{provider}': "
            f"{get_masked_api_key(existing_api_key)}"
        )
    else:
        print(f"  No API key found for '{provider}' in auth config")
    print()

    print("Authentication")
    print("-" * 30)
    api_key = _prompt_with_default(
        "Enter API key", default=existing_api_key, is_password=True
    )
    if not api_key:
        print("Error: API key is required.", file=sys.stderr)
        return None
    api_key = api_key.strip()
    print(f"  API key: {get_masked_api_key(api_key)}")
    print()
    return api_key


def _prompt_model(provider: str, existing_model: str | None) -> str | None:
    """Prompt for the model name; returns None to abort."""
    print("Model")
    print("-" * 30)
    # Default to the model already configured for the selected provider.
    default_model = load_model_from_config(provider) or existing_model
    model = _prompt_with_default("Enter model name", default=default_model)
    if not model:
        print("Error: Model name is required.", file=sys.stderr)
        return None
    model = model.strip()
    print(f"  Using model: {model}")
    print()
    return model


def _prompt_max_output_tokens(existing_max_output_tokens: int | None) -> int | None:
    """Prompt for the max output tokens; returns None to abort."""
    print("Max Output Tokens")
    print("-" * 30)
    default_max_tokens = (
        existing_max_output_tokens if existing_max_output_tokens else 65536
    )
    max_tokens_str = _prompt_with_default(
        "Enter max output tokens", default=str(default_max_tokens)
    )
    if not max_tokens_str:
        return 65536
    try:
        max_output_tokens = int(max_tokens_str.strip())
    except ValueError:
        print("Error: Max output tokens must be a number.", file=sys.stderr)
        return None
    print(f"  Using max output tokens: {max_output_tokens}")
    print()
    return max_output_tokens


def _prompt_custom_endpoint(provider: str, existing_endpoint: str | None) -> str | None:
    """Prompt for the endpoint (required for 'custom' provider); None to abort."""
    print("Endpoint (required for 'custom' provider)")
    print("-" * 30)
    # Default to the endpoint already configured for the selected provider.
    default_endpoint = load_endpoint_from_config(provider) or existing_endpoint
    endpoint = _prompt_with_default("Enter API endpoint URL", default=default_endpoint)
    if not endpoint:
        print("Error: Endpoint is required for 'custom' provider.", file=sys.stderr)
        return None
    endpoint = endpoint.strip()
    print(f"  Using endpoint: {endpoint}")
    print()
    return endpoint


def _save_configuration(
    provider: str,
    model: str,
    api_key: str,
    max_output_tokens: int,
    endpoint: str | None,
) -> int:
    """Persist the interactive configuration; returns the exit code."""
    try:
        # Save provider to config.json
        set_config_from_cli(f"provider={provider}")
        print(f"[OK] Saved provider '{provider}' to config")

        # Save model to config.json under the provider-scoped key
        # (e.g. "openai.model") so each provider has its own default model.
        set_config_from_cli(f"model={model}", provider)
        print(f"[OK] Saved model '{model}' to config ({provider}.model)")

        # Save max output tokens to config.json under the provider-scoped key
        # (e.g. "openai.max-output-tokens") so each provider has its own limit.
        set_config_from_cli(f"max-output-tokens={max_output_tokens}", provider)
        print(
            f"[OK] Saved max output tokens {max_output_tokens} to config "
            f"({provider}.max-output-tokens)"
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


def handle_config_interactive() -> int:
    """Handle --config command for interactive configuration setup.

    Prompts the user for:
    - Provider name (with existing config value as default)
    - API key (with existing auth value for that provider as default, masked)
    - Max output tokens (with existing config value as default, default 65536)
    - Endpoint (required only for 'custom' provider)

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Load existing values
    existing_provider = load_provider_from_config()
    existing_model = load_model_from_config(existing_provider)
    existing_max_output_tokens = load_max_output_tokens(existing_provider)
    existing_endpoint = load_endpoint_from_config()

    print("\n" + "=" * 50)
    print("  janito Interactive Configuration")
    print("=" * 50)
    print()

    provider = _prompt_provider(existing_provider)
    if provider is None:
        return 1

    api_key = _prompt_api_key(provider)
    if api_key is None:
        return 1

    model = _prompt_model(provider, existing_model)
    if model is None:
        return 1

    max_output_tokens = _prompt_max_output_tokens(existing_max_output_tokens)
    if max_output_tokens is None:
        return 1

    endpoint = None
    if is_custom_provider(provider):
        endpoint = _prompt_custom_endpoint(provider, existing_endpoint)
        if endpoint is None:
            return 1

    # Confirm changes
    print("=" * 50)
    print("Configuration Summary:")
    print("-" * 30)
    print(f"  Provider:          {provider}")
    print(f"  Model:             {model}")
    print(f"  API Key:           {get_masked_api_key(api_key)}")
    print(f"  Max Output Tokens:    {max_output_tokens}")
    if endpoint:
        print(f"  Endpoint:          {endpoint}")
    print("=" * 50)
    print()

    confirm = input("Save these settings? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("Configuration cancelled.")
        return 0

    return _save_configuration(provider, model, api_key, max_output_tokens, endpoint)
