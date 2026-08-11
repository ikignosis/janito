"""Provider listing CLI handler (--show-providers)."""

from ...auth_config import get_api_key, get_auth_file_path
from ...general_config import (
    get_active_provider,
    get_config_path,
    get_masked_api_key,
    load_endpoint_from_config,
    load_model_from_config,
)
from ...provider_config import (
    CUSTOM_ENDPOINT_MARKER,
    PROVIDER_INFO,
    get_default_api_type_from_provider,
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_endpoint_for_api_type,
    get_supported_api_types_from_provider,
    list_variants,
    parse_variant_name,
)


def _format_token_limit(value: int | None) -> str:
    """Format a token limit for display (e.g. 1050000 -> '1050000')."""
    return f"{value:,}" if value is not None else "(none)"


def _resolve_endpoint_display(provider: str) -> tuple[str, str]:
    """Resolve the effective endpoint and its source label for a provider.

    Mirrors the runtime resolution: a configured endpoint override wins,
    otherwise the provider's built-in default resolved for its default API
    type (honoring ``endpoint_by_api_type``, e.g. Anthropic's native-SDK URL).

    Returns:
        A ``(endpoint, source)`` tuple ready for display.
    """
    config_endpoint = load_endpoint_from_config(provider)
    if config_endpoint:
        return config_endpoint, "configured"

    built_in = get_endpoint_for_api_type(
        provider, get_default_api_type_from_provider(provider)
    )
    if built_in is None:
        return "", "default OpenAI (no custom base URL)"
    if built_in == CUSTOM_ENDPOINT_MARKER:
        return "", "custom (set endpoint with --set endpoint=URL)"
    return built_in, "built-in"


def _print_provider_block(
    name: str,
    *,
    active: bool,
    variant_of: str | None = None,
) -> None:
    """Print one provider (or variant) block to stdout."""
    is_variant = variant_of is not None
    header = f"  {name}"
    if is_variant:
        header += f" (variant of {variant_of})"
    if active:
        header += " [active]"
    print(header)

    # Model: configured override first, otherwise the built-in default
    # (resolved through the base provider for variants).
    configured_model = load_model_from_config(name)
    default_model = get_default_model_from_provider(name)
    if configured_model:
        model_display = configured_model
        if default_model and default_model != configured_model:
            model_display += f" (configured; default {default_model})"
        else:
            model_display += " (configured)"
    elif default_model:
        model_display = f"{default_model} (default)"
    else:
        model_display = "(not set)"
    print(f"    Model:         {model_display}")

    # API types: the first entry is the built-in default.
    api_types = get_supported_api_types_from_provider(name) or []
    default_api_type = get_default_api_type_from_provider(name)
    if api_types:
        api_types_display = ", ".join(
            f"{api_type} (default)" if api_type == default_api_type else api_type
            for api_type in api_types
        )
    else:
        api_types_display = "(none)"
    print(f"    API types:     {api_types_display}")

    # Effective endpoint (configured override or built-in default).
    endpoint, endpoint_source = _resolve_endpoint_display(name)
    print(f"    Endpoint:      {endpoint or endpoint_source}")

    # API key (masked for display).
    api_key = get_api_key(name)
    api_key_display = f"{get_masked_api_key(api_key)} (set)" if api_key else "(not set)"
    print(f"    API key:       {api_key_display}")

    # Thinking mode default.
    thinking = get_default_thinking_from_provider(name)
    print(f"    Thinking:      {'enabled' if thinking else 'disabled'}")

    # Reasoning level default, when the provider declares one.
    reasoning = get_default_reasoning_level_from_provider(name)
    if reasoning:
        print(f"    Reasoning:     {reasoning} (default)")

    # Token limits.
    max_input = get_default_max_input_tokens_from_provider(name)
    max_output = get_default_max_output_tokens_from_provider(name)
    if max_input is not None or max_output is not None:
        print(
            f"    Max tokens:    {_format_token_limit(max_input)} in / {_format_token_limit(max_output)} out"
        )

    print()


def handle_show_providers(args) -> int:
    """Handle --show-providers command.

    Lists every supported provider from ``PROVIDER_INFO`` (with its built-in
    default model, API types, endpoint, token limits, thinking/reasoning
    defaults and API-key status) followed by the registered provider variants
    (``<provider>-<word>``, marked with their base provider). The configured
    default provider is flagged ``[active]``.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    active_provider = get_active_provider()

    # Built-in providers, in registry order; variants appended afterwards
    # (sorted), matching the web UI's provider list.
    entries = [(name, None) for name in PROVIDER_INFO]
    entries += [
        (variant, parse_variant_name(variant)[0]) for variant in list_variants()
    ]

    total = len(entries)
    print(f"Supported Providers ({total}):")
    print("=" * 60)

    for name, variant_of in entries:
        _print_provider_block(
            name,
            active=(name.lower() == (active_provider or "").lower()),
            variant_of=variant_of,
        )

    print("=" * 60)
    print(f"Config file:  {get_config_path()}")
    auth_path = get_auth_file_path()
    if auth_path.exists():
        print(f"Auth file:    {auth_path}")
    print()
    print(
        "Use --provider <name> to select one, or janito --create-variant <provider>-<word> to add a variant."
    )
    return 0
