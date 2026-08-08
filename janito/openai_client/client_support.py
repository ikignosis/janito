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

import logging
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

# Import MCP manager
from janito.mcp_manager import get_mcp_manager

# Configure logger for this module
logger = logging.getLogger(__name__)


def format_tokens(count):
    """Convert a token count to a human-readable format.

    Examples:
        2000 -> "2k"
        4000000 -> "4m"
        150 -> "150"
        12345 -> "12.3k"
    """
    if count is None:
        return None
    try:
        value = float(count)
    except (TypeError, ValueError):
        return count

    def _format(number):
        # Trim trailing ".0" for whole numbers (e.g. "2.0k" -> "2k")
        if number == int(number):
            return str(int(number))
        return f"{number:.1f}"

    if value >= 1_000_000:
        return f"{_format(value / 1_000_000)}m"
    if value >= 1_000:
        return f"{_format(value / 1_000)}k"
    return str(int(value))


def _load_mcp(use_mcp: bool) -> tuple[Any, list[dict[str, Any]]]:
    """Load MCP services/tools when enabled; return ``(manager, tools)``."""
    mcp_manager = None
    if use_mcp:
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
) -> None:
    """Print the token usage summary line.

    The token attribute names differ per API: Chat Completions reports
    ``prompt_tokens``/``completion_tokens`` (with ``prompt_tokens_details``),
    the Responses API reports ``input_tokens``/``output_tokens`` (with
    ``input_tokens_details``), and the native SDKs (Anthropic / DashScope)
    build a ``SimpleNamespace`` with ``input_tokens``/``output_tokens`` and no
    cached-token details.  Pass ``cached_details_attr=None`` to skip the
    cached-token read for APIs that do not report it.

    Args:
        usage_info: The usage object from the API response.
        max_input_tokens: The context-window limit for the "In:" ratio.
        max_output_tokens: The output-token limit for the "Out:" ratio.
        message_count: Number of messages/responses chained this turn.
        console: The Rich console to print to.
        label: What ``message_count`` counts ("Messages" or "Responses").
        input_attr: Attribute holding the input-token count.
        output_attr: Attribute holding the output-token count.
        cached_details_attr: Attribute holding the cached-token details, or
            ``None`` when the API does not report cached tokens.
    """
    total_tokens = getattr(usage_info, "total_tokens", None)
    input_tokens = getattr(usage_info, input_attr, None)
    output_tokens = getattr(usage_info, output_attr, None)
    cached_tokens = None
    details = (
        getattr(usage_info, cached_details_attr, None)
        if cached_details_attr is not None
        else None
    )
    if details:
        cached_tokens = getattr(details, "cached_tokens", None)

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

    token_text = Text(f"=== {' | '.join(parts)} ===")
    token_text.stylize("white on magenta")
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
    from janito.general_config import get_active_provider, get_masked_api_key

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
