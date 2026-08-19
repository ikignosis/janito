"""Provider listing CLI handler (--show-providers)."""

from ...auth_config import get_api_key, get_auth_file_path
from ...config_keys import get_masked_api_key
from ...config_loaders import load_endpoint_from_config, load_model_from_config
from ...config_store import get_config_path
from ...general_config import get_active_provider
from ...provider_accessors import (
    format_thinking_display,
    get_default_api_type_from_provider,
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_model_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_default_tools_from_provider,
    get_endpoint_for_api_type,
    get_supported_api_types_from_provider,
)
from ...provider_registry import ProviderRegistry, parse_variant_name
from ...provider_validation import list_variants
from ...providers import CUSTOM_ENDPOINT_MARKER

_registry = ProviderRegistry()


def _format_token_limit(value: int | None) -> str:
    """Format a token limit for display (e.g. 1050000 -> '1050000')."""
    return f"{value:,}" if value is not None else "(none)"


def _tools_display(provider: str, model: str) -> str | None:
    """Format the model's built-in tools per API type for display.

    Each supported API type that has built-in tools contributes a
    ``"type1, type2 (API Type)"`` segment, e.g. ``"code_interpreter,
    web_search, web_extractor (Responses)"``.  Returns ``None`` when no API
    type has built-in tools.
    """
    segments = []
    for api_type in get_supported_api_types_from_provider(provider, model) or []:
        tools = get_default_tools_from_provider(provider, model, api_type=api_type)
        if tools:
            joined = ", ".join(
                tool.get("type") if isinstance(tool, dict) else str(tool)
                for tool in tools
            )
            segments.append(f"{joined} ({api_type})")
    return "; ".join(segments) or None


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


def _model_rows(
    provider: str, model: str, *, default_model: str | None
) -> list[tuple[str, str]]:
    """Build the (key, value) rows describing one built-in model entry."""
    rows: list[tuple[str, str]] = []
    label = model
    if default_model and model == default_model:
        label += " (default)"

    api_types = get_supported_api_types_from_provider(provider, model) or []
    default_api_type = get_default_api_type_from_provider(provider, model)
    if api_types:
        api_types_display = ", ".join(
            f"{api_type} (default)" if api_type == default_api_type else api_type
            for api_type in api_types
        )
    else:
        api_types_display = "(none)"
    rows.append((f"{label} API types", api_types_display))

    thinking = get_default_thinking_from_provider(provider, model)
    rows.append(
        (f"{label} thinking", format_thinking_display(thinking, provider=provider))
    )

    # Built-in (native) tools are resolved per API type: each supported
    # API type that declares tools is shown as "type1, type2 (API Type)".
    # Models without built-in tools (or whose tools are disabled for every
    # API type) get no row.
    tools_display = _tools_display(provider, model)
    if tools_display:
        rows.append((f"{label} tools", tools_display))

    reasoning = get_default_reasoning_level_from_provider(provider, model)
    if reasoning:
        rows.append((f"{label} reasoning", f"{reasoning} (default)"))

    max_input = get_default_max_input_tokens_from_provider(provider, model)
    max_output = get_default_max_output_tokens_from_provider(provider, model)
    if max_input is not None or max_output is not None:
        rows.append(
            (
                f"{label} max tokens",
                f"{_format_token_limit(max_input)} in / {_format_token_limit(max_output)} out",
            )
        )
    return rows


def _provider_rows(
    name: str,
    *,
    variant_of: str | None = None,
) -> list[tuple[str, str]]:
    """Build the (key, value) rows describing one provider or variant."""
    rows: list[tuple[str, str]] = []

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
    rows.append(("Model", model_display))

    # Effective endpoint (configured override or built-in default).
    endpoint, endpoint_source = _resolve_endpoint_display(name)
    rows.append(("Endpoint", endpoint or endpoint_source))

    # API key (masked for display).
    api_key = get_api_key(name)
    api_key_display = f"{get_masked_api_key(api_key)} (set)" if api_key else "(not set)"
    rows.append(("API key", api_key_display))

    # Per-model rows: every built-in model entry with its capabilities and
    # defaults (the default model is marked).  Variants inherit the base
    # provider's ``models`` dict, so they list the same models.
    provider = _registry.get(name)
    for model in provider.model_names() if provider is not None else []:
        rows.extend(_model_rows(name, model, default_model=default_model))

    return rows


def handle_show_providers(args) -> int:
    """Handle --show-providers command.

    Lists every supported provider (with its built-in default model,
    endpoint, API-key status and a per-model breakdown of API types,
    thinking/reasoning defaults and token limits) followed by the
    registered provider variants (``<provider>-<word>``, marked with their
    base provider). Each provider is rendered as a rich two-column table.
    The configured default provider is flagged ``[active]``.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from rich.console import Console
    from rich.table import Table

    active_provider = get_active_provider()

    # Built-in providers, in registry order; variants appended afterwards
    # (sorted), matching the web UI's provider list.
    entries = [(name, None) for name in _registry.names()]
    entries += [
        (variant, parse_variant_name(variant)[0]) for variant in list_variants()
    ]

    total = len(entries)
    print(f"Supported Providers ({total}):")
    print()

    console = Console(markup=False)
    for name, variant_of in entries:
        header = name
        if variant_of is not None:
            header += f" (variant of {variant_of})"
        if name.lower() == (active_provider or "").lower():
            header += " [active]"

        table = Table(
            title=header,
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Key", style="green", no_wrap=True)
        table.add_column("Value", overflow="fold")
        for key, value in _provider_rows(name, variant_of=variant_of):
            table.add_row(key, value)
        console.print(table)

    print(f"Config file:  {get_config_path()}")
    auth_path = get_auth_file_path()
    if auth_path.exists():
        print(f"Auth file:    {auth_path}")
    print()
    print(
        "Use --provider <name> to select one, or janito --create-variant <provider>-<word> to add a variant."
    )
    return 0
