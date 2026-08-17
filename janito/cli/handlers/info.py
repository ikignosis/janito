"""Info and configuration display CLI handlers."""

from ...auth_config import get_api_key, get_auth_file_path
from ...config_keys import get_masked_api_key
from ...config_loaders import load_endpoint_from_config, load_model_from_config
from ...config_store import get_config_path
from ...general_config import load_provider_from_config, resolve_api_type
from ...provider_accessors import (
    format_thinking_display,
    get_default_model_from_provider,
    get_default_thinking_from_provider,
    get_endpoint_for_api_type,
    get_responses_in_server_from_provider,
)
from ...provider_validation import is_custom_provider
from ...providers import CUSTOM_ENDPOINT_MARKER


def _resolve_provider_source(args) -> tuple[str, str]:
    """Resolve the provider, with priority CLI > config.json > fallback."""
    cli_provider = getattr(args, "provider", None)

    # 1. Check CLI argument directly
    if cli_provider:
        return cli_provider, "CLI argument"
    # 2. Check config.json for provider
    config_provider = load_provider_from_config()
    if config_provider:
        return config_provider, "config.json"
    # 3. Fall back to 'openai'
    return "openai", "fallback"


def _resolve_model_source(
    provider: str, cli_model: str | None
) -> tuple[str | None, str]:
    """Resolve the model, with priority CLI > config."""
    if cli_model:
        return cli_model, "CLI argument"
    config_model = load_model_from_config(provider)
    if config_model:
        return config_model, f"config.json ({provider}.model)"
    return None, "not set"


def _resolve_endpoint_source(provider: str, api_type: str) -> tuple[str | None, str]:
    """Resolve the endpoint/base URL, with priority config > provider default."""
    config_endpoint = load_endpoint_from_config(provider)
    if config_endpoint:
        return config_endpoint, f"config.json ({provider}.endpoint)"
    if is_custom_provider(provider):
        return None, "required but not set (set endpoint in config.json)"
    provider_default = get_endpoint_for_api_type(provider, api_type)
    if provider_default and provider_default != CUSTOM_ENDPOINT_MARKER:
        return provider_default, f"{provider} default"
    if provider_default is None:
        return None, "default OpenAI"
    return None, "not set"


def _resolve_effective_model(
    provider: str | None, cli_model: str | None
) -> tuple[str | None, str]:
    """Resolve the effective model, mirroring ``resolve_runtime_config``.

    Priority: ``--model``, then the provider's configured model in
    config.json, and finally the provider's built-in default model.

    Returns:
        Tuple of (model, source). ``model`` is ``None`` when neither the
        provider nor its built-in defaults define one (e.g. ``custom``).
    """
    model = cli_model or load_model_from_config(provider)
    if model:
        return model, "CLI argument" if cli_model else f"{provider}.model"
    return get_default_model_from_provider(provider), f"{provider} default"


def handle_info(args) -> int:
    """Handle --info command.

    Prints information about the resolved configuration and exits.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    provider, provider_source = _resolve_provider_source(args)

    model, model_source = _resolve_model_source(provider, getattr(args, "model", None))

    # Determine API key (from auth.json for the resolved provider)
    api_key = get_api_key(provider)
    api_key_source = f"auth.json (provider: {provider})" if api_key else "not set"

    # Determine the effective API type first (--api-type, then the
    # model-scoped configured api-type, then the effective model's built-in
    # default) so the built-in endpoint can be resolved per API type
    # (endpoint_by_api_type).
    api_type = resolve_api_type(
        getattr(args, "api_type", None), provider, getattr(args, "model", None)
    )

    endpoint, endpoint_source = _resolve_endpoint_source(provider, api_type)

    from rich.console import Console
    from rich.table import Table

    rows = [
        ("Provider", f"{provider} ({provider_source})"),
        ("Model", f"{model or '(not set)'} ({model_source})"),
        ("API Type", api_type),
    ]
    if api_type == "Responses":
        responses_in_server = get_responses_in_server_from_provider(provider, model)
        responses_display = (
            "server-side (previous_response_id)"
            if responses_in_server
            else "stateless (client re-sends history)"
        )
        rows.append(("Responses In Server", responses_display))
    rows.append(("API Key", f"{get_masked_api_key(api_key)} ({api_key_source})"))
    rows.append(("Endpoint", f"{endpoint or '(not set)'} ({endpoint_source})"))

    table = Table(
        title="Resolved Configuration",
        title_style="bold",
        header_style="bold cyan",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_column("Key", style="green", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for key, value in rows:
        table.add_row(key, value)
    Console(markup=False).print(table)

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
    for security) from config files. The model shown is the effective model
    for the active provider: ``--model``, then ``<provider>.model`` from
    config.json, and finally the provider's built-in default model.

    Args:
        args: Parsed command line arguments (optional). Used to honor
            ``--provider`` and ``--model`` when displaying the model.

    Returns:
        int: Exit code (0 for success)
    """
    # Load configured values from config.json
    cli_provider = getattr(args, "provider", None) if args is not None else None
    provider = cli_provider or load_provider_from_config()

    # Resolve the effective model, mirroring the runtime resolution in
    # resolve_runtime_config (see _resolve_effective_model).
    cli_model = getattr(args, "model", None) if args is not None else None
    model, model_source = _resolve_effective_model(provider, cli_model)

    # Resolve API key from the auth store and determine its source
    api_key = get_api_key(provider) if provider else None
    api_key_source = "auth.json" if api_key else "not set"

    # Resolve the endpoint, mirroring the runtime resolution in
    # resolve_runtime_config: config.json endpoint > provider's built-in base
    # URL (resolved for the effective API type). Displaying this makes
    # key/endpoint mismatches (e.g. a token-plan key sent to the dashscope
    # endpoint) visible.
    endpoint = None
    endpoint_source = "not set"
    api_type = resolve_api_type(
        getattr(args, "api_type", None) if args is not None else None,
        provider,
        model,
    )
    config_endpoint = load_endpoint_from_config(provider)
    if config_endpoint:
        endpoint = config_endpoint
        endpoint_source = "config.json"
    elif provider and not is_custom_provider(provider):
        provider_base = get_endpoint_for_api_type(provider, api_type)
        if provider_base and provider_base != CUSTOM_ENDPOINT_MARKER:
            endpoint = provider_base
            endpoint_source = f"{provider} default"
        elif provider_base is None:
            endpoint_source = "default OpenAI"
    elif provider and is_custom_provider(provider):
        endpoint_source = "required but not set (set endpoint in config.json)"

    # Resolve the effective thinking mode: the CLI --thinking flag first,
    # otherwise the effective model's built-in default (True for DeepSeek
    # and Alibaba/Qwen; a pass-through dict such as {'type': 'adaptive'}
    # for MiniMax-M3).
    thinking = getattr(args, "thinking", False) or get_default_thinking_from_provider(
        provider, model
    )
    thinking_display = format_thinking_display(thinking)
    if thinking and not getattr(args, "thinking", False):
        thinking_display += " (model default)"

    from rich.console import Console
    from rich.table import Table

    table = Table(
        title="Current Configuration",
        title_style="bold",
        header_style="bold cyan",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_column("Key", style="green", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Provider", provider or "(not configured)")
    if model:
        table.add_row("Model", f"{model} ({model_source})")
    else:
        table.add_row("Model", "(not configured)")
    table.add_row("API Type", api_type)
    masked = get_masked_api_key(api_key)
    if api_key:
        table.add_row("API Key", f"{masked} ({api_key_source})")
    else:
        table.add_row("API Key", "(not set)")
    if endpoint:
        table.add_row("Endpoint", f"{endpoint} ({endpoint_source})")
    else:
        table.add_row("Endpoint", f"(default OpenAI) ({endpoint_source})")
    table.add_row("Thinking", thinking_display)
    Console(markup=False).print(table)

    return 0


def handle_show_system_prompt(args) -> int:
    """Handle --show-system-prompt command.

    Resolves and displays the effective system prompt based on the current
    CLI flags (-S, -Z) and exits.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from rich.console import Console
    from rich.table import Table

    from ...system_prompt import SECTION_SKILLS, sync_default_sections

    console = Console(markup=False)

    if args.system_prompt:
        prompt = args.system_prompt
        source = "CLI override (-S)"
        table = Table(
            title=f"System prompt ({source})",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
        )
        table.add_column("Content", overflow="fold")
        table.add_row(prompt.strip())
        console.print(table)
        return 0

    if args.no_system_prompt:
        print("System prompt: (disabled via -Z / --no-system-prompt)")
        return 0

    # Default prompt: render each section as a rich table row (Section, Lines,
    # Content), matching the shell /prompt command.  Only advertise skills in
    # the title when a "skills" section is actually present (skills enabled and
    # at least one skill advertised).
    manager = sync_default_sections()
    sections = list(manager.get_all_sections())
    has_skills = any(name == SECTION_SKILLS for name, _ in sections)
    title = (
        "System prompt (default (with skills))"
        if has_skills
        else "System prompt (default)"
    )
    table = Table(
        title=title,
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Section", style="green", no_wrap=True)
    table.add_column("Lines", justify="right")
    table.add_column("Content", overflow="fold")
    for name, text in sections:
        body = text.rstrip()
        line_count = len(body.splitlines()) if body else 0
        table.add_row(name, str(line_count), body)
        # Empty row after each section for visual context split.
        table.add_row("", "", "")
    console.print(table)

    return 0
