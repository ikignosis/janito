"""
Shared module-level helpers for the Chat Completions client.

Extracted from :mod:`janito.openai_client.completions_api` so the client
module stays focused on the ``send_prompt`` entry point, the
:class:`CompletionsClient` class and the shared runtime helpers
(``resolve_runtime_config``, progress bar, Enter-cancel detection).
"""

import logging
from typing import Any

from rich.console import Console

# Import general configuration handling
from janito.config_loaders import (
    load_max_input_tokens,
    load_max_output_tokens,
    load_reasoning_level,
)

# Import provider configuration for base URLs and built-in defaults
from janito.provider_accessors import (
    apply_thinking_to_extra_body,
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
)

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files

# Shared client helpers (Rich console output, usage summary)
from .client_support import _display_usage

# Configure logger for this module
logger = logging.getLogger(__name__)


def _resolve_tools(
    tools: list[dict[str, Any]] | None, mcp_tools: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve the tool schemas (built-in + MCP)."""
    if tools is None:
        # Merge built-in tools with MCP tools
        built_in_tools = get_all_tool_schemas()
        tools_schemas = built_in_tools + mcp_tools
        logger.debug(
            f"Using {len(built_in_tools)} built-in tools + {len(mcp_tools)} MCP tools"
        )
    else:
        tools_schemas = tools
        logger.debug(f"Using {len(tools_schemas)} provided tools")
    return tools_schemas


def _resolve_model_settings(
    provider: str,
    model: str,
    thinking: bool,
    reasoning_level: str | None,
) -> tuple[bool, int | None, int | None, str | None]:
    """Resolve thinking mode, token limits and reasoning level for ``model``.

    Returns ``(thinking, max_output_tokens, max_input_tokens,
    reasoning_level)`` where ``thinking`` is the resolved value: the
    explicit ``--thinking`` flag (``True``) when given, otherwise the
    model's built-in default (a ``True`` flag or a pass-through dict such as
    MiniMax-M3's ``{'type': 'adaptive'}``).  See
    :func:`apply_thinking_to_extra_body`.
    """
    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # model's built-in default applies (True for DeepSeek and Alibaba/Qwen,
    # a dict for MiniMax-M3, which reason by default). See
    # provider_data.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider, model)
    max_output_tokens = load_max_output_tokens(provider, model)
    if max_output_tokens is None:
        # Fall back to the model's built-in default (from PROVIDER_INFO),
        # then to a global default of 100k tokens.
        max_output_tokens = get_default_max_output_tokens_from_provider(provider, model)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the model's max input tokens (context window) for the usage
    # summary display: a config override (--set max-input-tokens=... or the
    # interactive --config wizard) wins, otherwise the model's built-in
    # default applies.
    max_input_tokens = load_max_input_tokens(provider, model)
    if max_input_tokens is None:
        max_input_tokens = get_default_max_input_tokens_from_provider(provider, model)

    # Reasoning level (reasoning_effort): --reasoning-level CLI arg, then the
    # model-scoped configured value (--set reasoning-level=...), and finally
    # the model's built-in default (from PROVIDER_INFO, e.g. "xhigh" for
    # Alibaba's qwen3.8-max). None means the API's own default applies.
    reasoning_level = reasoning_level or load_reasoning_level(provider, model)
    if reasoning_level is None:
        reasoning_level = get_default_reasoning_level_from_provider(provider, model)
    return thinking, max_output_tokens, max_input_tokens, reasoning_level


def _build_call_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    max_output_tokens: int | None,
    reasoning_level: str | None,
    preserve_thinking: Any,
    thinking,
) -> dict[str, Any]:
    """Build the Chat Completions call parameters for one round."""
    call_kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 1.0,
    }

    # Add max_tokens if max output tokens is set in config
    if max_output_tokens is not None:
        call_kwargs["max_completion_tokens"] = max_output_tokens

    # Pass the reasoning level (reasoning_effort) when resolved.
    if reasoning_level:
        call_kwargs["reasoning_effort"] = reasoning_level

    # Pass preserve_thinking in extra_body if defined in config
    if preserve_thinking is not None:
        call_kwargs.setdefault("extra_body", {})[
            "preserve_thinking"
        ] = preserve_thinking

    # Pass the thinking mode in extra_body: enable_thinking for flag-style
    # defaults, or the raw dict for providers with a structured thinking
    # parameter (e.g. MiniMax-M3's {"type": "adaptive"}).
    apply_thinking_to_extra_body(call_kwargs, thinking)

    call_kwargs["stream"] = True
    call_kwargs["stream_options"] = {"include_usage": True}
    return call_kwargs


def _handle_not_found_error(
    e: Exception,
    base_url: str | None,
    model: str,
    console: Console,
) -> None:
    """Explain NotFoundError (unknown model) and re-raise."""
    if "Model not exist" in str(e) or "model not exist" in str(e).lower():
        api_url = base_url if base_url else "https://api.openai.com"
        console.print(
            f"[bold red]Error: Model not found.[/bold red] "
            f"Current model being used: [bold]{model}[/bold] | API URL: [bold]{api_url}[/bold]"
        )
        console.print(
            "[dim]Please check that the model name is correct and available "
            "for your API key/provider.[/dim]"
        )
        logger.error(f"Model '{model}' not found at API URL '{api_url}': {e}")


def _finalize_response(
    full_content: str,
    reasoning_content: str | None,
    messages: list[dict[str, Any]],
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int | None,
    console: Console,
) -> str:
    """Record the assistant message, print the end-of-turn reports and return."""
    # Build the assistant message with reasoning_content if available
    assistant_message = {"role": "assistant", "content": full_content}
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content

    # Add assistant message to conversation history
    messages.append(assistant_message)

    # Display the tracked used files before the token usage summary.
    # Nothing is printed when no files were tracked (empty Text).
    used_files_report = format_used_files()
    if used_files_report:
        console.print(used_files_report, highlight=False)

    # Display token usage with magenta background
    if usage_info:
        _display_usage(
            usage_info,
            max_input_tokens,
            max_output_tokens,
            len(messages),
            console,
            label="Messages",
            input_attr="prompt_tokens",
            output_attr="completion_tokens",
            cached_details_attr="prompt_tokens_details",
        )
    return full_content
