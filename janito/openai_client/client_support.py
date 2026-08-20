"""
Shared helpers for the OpenAI-compatible client modules.

The four client modules (``completions_api``, ``conversations_api``,
``anthropic_api`` and ``dashscope_api``) duplicate a set of small, generic
helpers: token formatting, MCP loading, Rich console output (verbose banner,
reasoning panel, markdown content, token-usage summary) and the
authentication-error explainer.  This module centralizes them so each client
stays focused on its own API's wire format.

The ``_run_with_progress_bar`` runner stays in
:mod:`janito.openai_client.completions_api` (it is monkeypatched by tests
through that module's namespace); every client re-uses it from there.
"""

import json
import logging
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

# Shared usage normalization (also used by the web loop's UsageEvent).
from janito.agent.usage import format_tokens, normalize_usage

# Import MCP manager
from janito.mcp_manager import get_mcp_manager
from janito.provider_accessors import get_provider_cost
from janito.tooling.tools_registry import tools_loading_enabled

# Configure logger for this module
logger = logging.getLogger(__name__)


def _load_mcp(use_mcp: bool) -> tuple[Any, list[dict[str, Any]]]:
    """Load MCP services/tools when enabled; return ``(manager, tools)``.

    MCP tools are never loaded when tool loading is disabled (``--no-tools``):
    that flag suppresses every non-skill tool, MCP included.
    """
    mcp_manager = None
    if use_mcp and tools_loading_enabled():
        mcp_manager = get_mcp_manager()
        try:
            mcp_manager.load_services()
            mcp_tools = mcp_manager.get_all_tools()
            logger.info(
                f"Loaded {len(mcp_tools)} MCP tools from "
                f"{len(mcp_manager.connected_services)} services"
            )
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
            mcp_tools = []
    else:
        mcp_tools = []
    return mcp_manager, mcp_tools


def _print_verbose_info(
    console: Console,
    base_url: str | None,
    model: str,
    mcp_manager,
    backend_default: str,
) -> None:
    """Print model/backend/MCP info in verbose mode.

    Args:
        console: The Rich console to print to.
        base_url: The resolved API base URL (``None`` for the standard
            OpenAI endpoint).
        model: The model name being used.
        mcp_manager: The MCP manager (may be ``None``).
        backend_default: The fallback backend label when ``base_url`` is
            ``None`` (e.g. ``"api.openai.com"``, ``"https://api.anthropic.com"``).
    """
    backend = base_url if base_url else backend_default
    text = Text(f"----- Model: {model} | Backend: {backend}")
    text.stylize("white on blue")
    console.print(text, highlight=False)

    # Show MCP status in verbose mode
    if mcp_manager and mcp_manager.connected_services:
        services_text = Text(
            f"----- MCP Services: {', '.join(mcp_manager.connected_services)}"
        )
        services_text.stylize("white on green")
        console.print(services_text, highlight=False)


def _truncate_text(value: Any, limit: int = 400) -> str:
    """Truncate long text for verbose output, marking the cut."""
    if value is None:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]} ... ({len(text) - limit} more chars)"


def _truncate_list(values: list, limit: int = 300) -> list:
    """Truncate each element of a list for verbose output."""
    out: list = []
    for value in values:
        if isinstance(value, dict):
            out.append(_truncate_item(value, limit))
        elif isinstance(value, list):
            out.append(_truncate_list(value, limit))
        elif isinstance(value, str):
            out.append(_truncate_text(value, limit))
        else:
            out.append(value)
    return out


def _truncate_item(item: dict, limit: int = 300) -> dict:
    """Recursively truncate a message/input item for verbose output."""
    out: dict = {}
    for key, value in item.items():
        if isinstance(value, str):
            out[key] = _truncate_text(value, limit)
        elif isinstance(value, list):
            out[key] = _truncate_list(value, limit)
        elif isinstance(value, dict):
            out[key] = _truncate_item(value, limit)
        else:
            out[key] = value
    return out


def _print_verbose_api_call(
    console: Console,
    call_kwargs: dict[str, Any],
    tools_schemas: list[dict[str, Any]] | None = None,
    *,
    tail: int = 3,
) -> None:
    """Print the API request parameters in verbose mode.

    The full ``messages`` / ``input`` conversation is too long to dump, so
    only the last ``tail`` entries are shown (with the total count noted) and
    every string inside them is truncated.  Tool schemas are summarized by
    name instead of printed in full; model capabilities carried under the
    reserved ``_builtin_tools`` key are summarized by ``type``.
    """
    display: dict[str, Any] = {}
    for key, value in call_kwargs.items():
        if key == "_builtin_tools":
            # Model capabilities (e.g. code_interpreter / web_search) are
            # merged into the tools array by the stream runner; summarize
            # them by type alongside the function-tool schemas.
            display[key] = [t.get("type") for t in (value or [])]
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            display[key] = {
                "_summary": (
                    f"{len(value)} items (showing last {tail})"
                    if len(value) > tail
                    else f"{len(value)} items"
                ),
                "tail": _truncate_list(value[-tail:]),
            }
        elif key in ("messages", "input") and isinstance(value, str):
            display[key] = _truncate_text(value, 500)
        else:
            display[key] = value

    if tools_schemas:
        names = [
            t.get("name") or (t.get("function") or {}).get("name") or t.get("type")
            for t in tools_schemas
        ]
        display["tools"] = {"_summary": f"{len(names)} tools", "names": names}

    console.print(
        Panel(
            json.dumps(display, indent=2, default=str),
            title=f"[bold blue]API Call: {call_kwargs.get('model', '?')}[/bold blue]",
            border_style="blue",
        ),
        highlight=False,
    )


def _object_items(obj: Any):
    """Yield ``(key, value)`` pairs from an SDK response object.

    Handles pydantic models (``model_dump``/``dict``), ``SimpleNamespace`` /
    plain objects (``__dict__``), plain dicts and dict-like objects
    (DashScope's ``DictMixin``).
    """
    if isinstance(obj, dict):
        return obj.items()
    for attr in ("model_dump", "dict"):
        method = getattr(obj, attr, None)
        if callable(method):
            try:
                if attr == "model_dump":
                    # Pydantic v2's model_dump accepts warnings=False; older
                    # pydantic v2 releases raise TypeError for the kwarg, so
                    # fall back to the plain call.  Suppressing serializer
                    # warnings keeps response metadata the SDK parsed with
                    # construct() (e.g. a provider echoing back a built-in
                    # tool type the SDK does not know, like Alibaba/Qwen's
                    # ``web_extractor``) from flooding the console during the
                    # raw-attribute dump: the echoed ``tools`` array is never
                    # surfaced anyway (only scalar top-level attributes are).
                    try:
                        return method(warnings=False).items()
                    except TypeError:
                        pass
                return method().items()
            except Exception:
                continue
    if hasattr(obj, "__dict__"):
        return vars(obj).items()
    if callable(getattr(obj, "keys", None)):
        try:
            return [(k, obj[k]) for k in obj.keys()]
        except Exception:
            return []
    return []


def _extract_raw_attrs(
    obj: Any, *, skip: tuple[str, ...] = (), max_list: int = 3
) -> dict[str, Any]:
    """Extract the scalar top-level attributes of an SDK response object.

    SDK response objects (pydantic models, ``SimpleNamespace``, DashScope's
    ``DictMixin``, plain dicts) expose their wire metadata as top-level
    attributes: ``id``, ``model``, ``created``, ``system_fingerprint``,
    ``status``, ``finish_reason``, ...  The verbose response dump should
    surface those alongside the already-extracted content/usage/tool-call
    fields, so this helper flattens them into a plain dict.

    Nested payloads (``choices``, ``output``, ``content``, ``usage``, ...)
    are omitted either via ``skip`` or because their values are not scalars
    (or are long lists of non-scalars), so the dump stays compact.
    """
    if obj is None:
        return {}
    out: dict[str, Any] = {}
    for key, value in _object_items(obj):
        if key.startswith("_") or key in skip or value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
            continue
        if isinstance(value, (list, tuple)) and all(
            isinstance(v, (str, int, float, bool)) for v in value
        ):
            if 0 < len(value) <= max_list:
                out[key] = list(value)
            continue
        if isinstance(value, dict) and all(
            isinstance(v, (str, int, float, bool)) for v in value.values()
        ):
            if 0 < len(value) <= max_list:
                out[key] = dict(value)
    return out


def _raw_attrs_lines(raw_attrs: dict[str, Any] | None) -> list[str]:
    """Format raw response attributes as one ``Raw <key>:`` line each."""
    if not raw_attrs:
        return []
    return [
        f"Raw {key}: {_truncate_text(value, 120)}"
        for key, value in sorted(raw_attrs.items())
    ]


def _print_verbose_api_response(
    console: Console,
    full_content: str,
    reasoning_content: str | None,
    tool_calls: list[dict[str, Any]] | None,
    usage_info: Any,
    response_id: str | None = None,
    raw_attrs: dict[str, Any] | None = None,
) -> None:
    """Print a compact summary of the API response in verbose mode.

    The full assistant text is already rendered by the normal display path;
    this panel shows a tail of the content plus the raw top-level response
    attributes, the reasoning tail, tool-call names, normalized token usage
    and the server-side response id (when the API reports one).
    """
    lines = [f"Content: {_truncate_text(full_content, 500) or '(empty)'}"]
    lines.extend(_raw_attrs_lines(raw_attrs))
    if reasoning_content:
        lines.append(f"Reasoning: {_truncate_text(reasoning_content, 300)}")
    if tool_calls:
        calls = ", ".join(
            f"{t.get('name', '?')}({_truncate_text(t.get('arguments', ''), 80)})"
            for t in tool_calls
        )
        lines.append(f"Tool calls: {calls}")
    if usage_info:
        stats = normalize_usage(usage_info)
        if stats:
            parts = []
            for label, key in (("Total", "total"), ("In", "input"), ("Out", "output")):
                if stats.get(key) is not None:
                    parts.append(f"{label}: {stats[key]}")
            if stats.get("cached") is not None:
                parts.append(f"Cached: {stats['cached']}")
            lines.append("Usage: " + " | ".join(parts))
    if response_id:
        lines.append(f"Response id: {response_id}")
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold yellow]API Response[/bold yellow]",
            border_style="yellow",
        ),
        highlight=False,
    )


def _display_reasoning(reasoning_content: str, console: Console) -> None:
    """Show the reasoning panel when the model produced reasoning text."""
    if reasoning_content:
        console.print(
            Panel(
                Markdown(reasoning_content),
                title="[bold cyan]\U0001f4ad Reasoning[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        logger.debug("Reasoning content displayed")


def _display_content(full_content: str, console: Console) -> None:
    """Display the assembled response using rich markdown."""
    if full_content:
        console.print(Markdown(full_content))


def _display_usage(
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int | None,
    message_count: int,
    console: Console,
    *,
    label: str = "Messages",
    input_attr: str = "prompt_tokens",
    output_attr: str = "completion_tokens",
    cached_details_attr: str | None = "prompt_tokens_details",
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """Print the token usage summary line.

    The token attribute names differ per API (Chat Completions reports
    ``prompt_tokens``/``completion_tokens`` with ``prompt_tokens_details``,
    the Responses API reports ``input_tokens``/``output_tokens`` with
    ``input_tokens_details``, and the native SDKs build a ``SimpleNamespace``
    with ``input_tokens``/``output_tokens`` and no cached-token details).
    The shared :func:`normalize_usage` maps every shape onto one dict, so the
    display no longer needs per-API attribute plumbing.  ``input_attr`` /
    ``output_attr`` are retained for signature compatibility; pass
    ``cached_details_attr=None`` to skip the cached-token read for APIs that
    do not report it.

    ``Cost: <cost>`` is computed through
    :func:`janito.provider_accessors.get_provider_cost` from the provider /
    model and the normalized token counts (cached input tokens are billed at
    the provider's cache-hit rate); it falls back to ``N/A`` when the
    provider or model is unknown, or when no cost module exists for the
    provider.
    """
    stats = normalize_usage(usage_info)
    if stats is None:
        return
    total_tokens = stats["total"]
    input_tokens = stats["input"]
    output_tokens = stats["output"]
    cached_tokens = stats["cached"] if cached_details_attr is not None else None

    parts = []
    if total_tokens is not None:
        parts.append(f"Total: {format_tokens(total_tokens)}")
    if input_tokens is not None:
        if max_input_tokens is not None:
            parts.append(
                f"In: {format_tokens(input_tokens)}/{format_tokens(max_input_tokens)}"
            )
        else:
            parts.append(f"In: {format_tokens(input_tokens)}")
    if output_tokens is not None:
        if max_output_tokens is not None:
            parts.append(
                f"Out: {format_tokens(output_tokens)}/{format_tokens(max_output_tokens)}"
            )
        else:
            parts.append(f"Out: {format_tokens(output_tokens)}")
    if cached_tokens is not None:
        parts.append(f"Cached: {format_tokens(cached_tokens)}")
    parts.append(f"{label}: {message_count}")
    if provider is not None and model is not None:
        cost = get_provider_cost(
            provider,
            model,
            input_tokens if input_tokens is not None else 0,
            output_tokens if output_tokens is not None else 0,
            cached_tokens if cached_tokens is not None else 0,
        )
    else:
        cost = "N/A"
    parts.append(f"Cost: {cost}")

    token_text = Text(f"=== {' | '.join(parts)} ===")
    token_text.stylize("bright_white on magenta")
    console.print(token_text, highlight=False)
    logger.info(
        f"Request completed: total={total_tokens} tokens "
        f"(in={input_tokens}, out={output_tokens}, "
        f"cached={cached_tokens}, max={max_output_tokens}), "
        f"{message_count} {label.lower()}"
    )


def _handle_auth_error(
    e: Exception,
    cli_provider: str | None,
    api_key: str,
    base_url: str | None,
    model: str,
    console: Console,
) -> None:
    """Explain an authentication failure (invalid API key) and re-raise.

    Works for the OpenAI SDK clients (called from an ``AuthenticationError``
    handler) and for the native-SDK clients (Anthropic / DashScope), which
    raise their own exception types: the failure is recognized by a 401
    status code or an ``InvalidApiKey`` error code.  When the exception does
    not look like an auth failure (e.g. a different HTTP error from a native
    SDK), nothing is printed and the caller re-raises as usual.
    """
    from janito.config_keys import get_masked_api_key
    from janito.general_config import get_active_provider

    status_code = getattr(e, "status_code", None)
    code = getattr(e, "code", None)
    if status_code != 401 and not (isinstance(code, str) and "InvalidApiKey" in code):
        return

    provider = cli_provider or get_active_provider()
    masked_key = get_masked_api_key(api_key)
    api_url = base_url if base_url else "https://api.openai.com"
    console.print(
        "[bold red]Error: Authentication failed (invalid API key).[/bold red]"
    )
    console.print(f"  Provider: [bold]{provider}[/bold]")
    console.print(f"  Model:    [bold]{model}[/bold]")
    console.print(f"  API URL:  [bold]{api_url}[/bold]")
    console.print(f"  API Key:  [bold]{masked_key}[/bold]")
    console.print(
        f"[dim]Please verify your API key for the '{provider}' provider "
        f"and try again.[/dim]"
    )
    logger.error(
        f"Authentication failed - provider: {provider}, model: {model}, "
        f"api_url: {api_url}, api_key: {masked_key}: {e}"
    )
