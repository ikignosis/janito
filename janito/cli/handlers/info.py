"""Info and configuration display CLI handlers."""

from ...auth_config import get_api_key, get_auth_file_path, get_default_provider
from ...general_config import (
    get_config_path,
    get_masked_api_key,
    load_endpoint_from_config,
    load_model_from_config,
    load_provider_from_config,
    resolve_api_type,
)
from ...provider_config import (
    CUSTOM_ENDPOINT_MARKER,
    get_base_url_from_provider,
    get_default_thinking_from_provider,
    get_responses_in_server_from_provider,
    is_custom_provider,
)


def handle_info(args) -> int:
    """Handle --info command.

    Prints information about the resolved configuration and exits.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    cli_provider = getattr(args, "provider", None)

    # Determine resolved provider (priority: config.json > auth.json default > fallback)
    provider = None
    provider_source = ""

    # 1. Check CLI argument directly
    if cli_provider:
        provider = cli_provider
        provider_source = "CLI argument"
    # 2. Check config.json for provider
    else:
        config_provider = load_provider_from_config()
        if config_provider:
            provider = config_provider
            provider_source = "config.json"
        else:
            # 3. Check auth.json for default provider
            default_provider = get_default_provider()
            if default_provider:
                provider = default_provider
                provider_source = "auth.json (default)"
            else:
                # 4. Fall back to 'openai'
                provider = "openai"
                provider_source = "fallback"

    # Determine resolved model (priority: CLI > config)
    model = None
    model_source = "not set"

    cli_model = getattr(args, "model", None)

    if cli_model:
        model = cli_model
        model_source = "CLI argument"
    else:
        config_model = load_model_from_config(provider)
        if config_model:
            model = config_model
            model_source = f"config.json ({provider}.model)"

    # Determine API key (from auth.json for the resolved provider)
    api_key = get_api_key(provider)
    if api_key:
        api_key_source = f"auth.json (provider: {provider})"
    else:
        api_key_source = "not set"

    # Determine endpoint/base URL (priority: config > provider default)
    config_endpoint = load_endpoint_from_config(provider)

    endpoint = None
    endpoint_source = "not set"

    if config_endpoint:
        endpoint = config_endpoint
        endpoint_source = f"config.json ({provider}.endpoint)"
    elif is_custom_provider(provider):
        endpoint_source = "required but not set (set endpoint in config.json)"
    else:
        provider_default = get_base_url_from_provider(provider)
        if provider_default and provider_default != CUSTOM_ENDPOINT_MARKER:
            endpoint = provider_default
            endpoint_source = f"{provider} default"
        elif provider_default is None:
            endpoint_source = "default OpenAI"

    # Print the info
    api_type = resolve_api_type(getattr(args, "api_type", None), provider)
    print("Resolved Configuration:")
    print("=" * 40)
    print(f"Provider:     {provider} ({provider_source})")
    print(f"Model:        {model or '(not set)'} ({model_source})")
    print(f"API Type:     {api_type}")
    if api_type == "Responses":
        responses_in_server = get_responses_in_server_from_provider(provider)
        responses_display = (
            "server-side (previous_response_id)"
            if responses_in_server
            else "stateless (client re-sends history)"
        )
        print(f"Responses In Server: {responses_display}")
    print(f"API Key:      {get_masked_api_key(api_key)} ({api_key_source})")
    print(f"Endpoint:     {endpoint or '(not set)'} ({endpoint_source})")
    print("=" * 40)
    print(f"Config file:  {get_config_path()}")

    # Try to show auth file path too
    auth_path = get_auth_file_path()
    if auth_path.exists():
        print(f"Auth file:    {auth_path}")

    print()

    # Show source details
    if model_source == "not set":
        print(
            "Note: Model not configured. Use --model or set it in config.json (janito --set model=NAME)"
        )
    if api_key_source == "not set":
        print("Note: API key not configured. Use --set-api-key --provider NAME")
    if is_custom_provider(provider) and not endpoint:
        print(
            "Note: Endpoint not configured. Set endpoint in config.json (janito --set endpoint=URL)"
        )

    return 0


def handle_show_config(args=None) -> int:
    """Handle --show-config command.

    Displays the currently configured provider, model, and API key (truncated
    for security) from config files. The model shown is the one configured for
    the active provider.

    Args:
        args: Parsed command line arguments (optional). Used to honor
            ``--provider`` when displaying the model.

    Returns:
        int: Exit code (0 for success)
    """
    # Load configured values from config.json
    cli_provider = getattr(args, "provider", None) if args is not None else None
    provider = cli_provider or load_provider_from_config()
    model = load_model_from_config(provider)

    # Resolve API key from the auth store and determine its source
    api_key = get_api_key(provider) if provider else None
    api_key_source = "auth.json" if api_key else "not set"

    # Resolve the endpoint, mirroring the runtime resolution in
    # resolve_runtime_config: config.json endpoint > provider's built-in base
    # URL. Displaying this makes key/endpoint mismatches (e.g. a token-plan key
    # sent to the dashscope endpoint) visible.
    endpoint = None
    endpoint_source = "not set"
    config_endpoint = load_endpoint_from_config(provider)
    if config_endpoint:
        endpoint = config_endpoint
        endpoint_source = "config.json"
    elif provider and not is_custom_provider(provider):
        provider_base = get_base_url_from_provider(provider)
        if provider_base and provider_base != CUSTOM_ENDPOINT_MARKER:
            endpoint = provider_base
            endpoint_source = f"{provider} default"
        elif provider_base is None:
            endpoint_source = "default OpenAI"
    elif provider and is_custom_provider(provider):
        endpoint_source = "required but not set (set endpoint in config.json)"

    # Resolve the effective thinking mode: the CLI --thinking flag first,
    # otherwise the provider's built-in default (True for DeepSeek and
    # Alibaba/Qwen).
    thinking = getattr(args, "thinking", False) or get_default_thinking_from_provider(
        provider
    )
    thinking_display = "enabled" if thinking else "disabled"
    if thinking and not getattr(args, "thinking", False):
        thinking_display += " (provider default)"

    print("Current Configuration:")
    print("=" * 40)
    print(f"Provider:  {provider or '(not configured)'}")
    if model:
        print(f"Model:     {model} ({provider}.model)")
    else:
        print("Model:     (not configured)")
    api_type = resolve_api_type(
        getattr(args, "api_type", None) if args is not None else None, provider
    )
    print(f"API Type:  {api_type}")
    masked = get_masked_api_key(api_key)
    if api_key:
        print(f"API Key:   {masked} ({api_key_source})")
    else:
        print("API Key:   (not set)")
    if endpoint:
        print(f"Endpoint:  {endpoint} ({endpoint_source})")
    else:
        print(f"Endpoint:  (default OpenAI) ({endpoint_source})")
    print(f"Thinking:  {thinking_display}")
    print("=" * 40)

    return 0


def handle_show_system_prompt(args) -> int:
    """Handle --show-system-prompt command.

    Resolves and displays the effective system prompt based on the current
    CLI flags (e.g., --gmail, --onedrive, -S, -Z) and exits.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from ...system_prompt import get_system_prompt_with_skills
    from ...tools.gmail import GMAIL_SYSTEM_PROMPT
    from ...tools.onedrive import ONEDRIVE_SYSTEM_PROMPT

    if args.system_prompt:
        prompt = args.system_prompt
        source = "CLI override (-S)"
    elif args.no_system_prompt:
        print("System prompt: (disabled via -Z / --no-system-prompt)")
        return 0
    elif args.onedrive:
        prompt = ONEDRIVE_SYSTEM_PROMPT
        source = "OneDrive mode (--onedrive)"
    elif args.gmail:
        prompt = GMAIL_SYSTEM_PROMPT
        source = "Gmail mode (--gmail)"
    else:
        prompt = get_system_prompt_with_skills()
        source = "default (with skills)"

    print(f"System prompt ({source}):")
    print("=" * 40)
    print(prompt)
    print("=" * 40)

    return 0
