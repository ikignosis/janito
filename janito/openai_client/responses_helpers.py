"""
Shared module-level helpers for the Responses API client.

Extracted from :mod:`janito.openai_client.conversations_api` so the client
module stays focused on the ``send_prompt`` entry point and the
:class:`ResponsesClient` class.
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

# Import provider configuration for built-in defaults
from janito.provider_accessors import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files

# Shared client helpers (Rich console output, usage summary) and the
# Responses API stream consumer.
from .client_support import _display_usage
from .responses_stream import _convert_tools_to_responses_format

# Configure logger for this module
logger = logging.getLogger(__name__)


def _pending_items_for_cancel(state: dict[str, Any]) -> list[dict[str, Any]] | None:
    """User messages to re-send after an Enter-cancel (server-side Responses).

    The aborted request's server-side response is discarded by the provider
    when the stream is interrupted (OpenAI answers ``previous_response_id not
    found`` for it), so the caller must not chain the next turn from it.
    Hand back the pending user messages (the cancelled prompt, plus any
    earlier cancelled prompts still awaiting a completed response in the
    caller's chain) so the next turn re-sends them as input items chained
    from the last completed response id.

    Returns ``None`` only when the state carries neither pending items nor a
    string prompt (defensive; the real flow always builds one of the two).
    """
    pending = state.get("pending_items")
    if pending:
        return [dict(item) for item in pending]
    input_items = state.get("input_items")
    if isinstance(input_items, str):
        return [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": input_items}],
            }
        ]
    return None


def _resolve_tools(
    tools: list[dict[str, Any]] | None, mcp_tools: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve the tool schemas (built-in + MCP) and convert to Responses format."""
    if tools is None:
        built_in_tools = get_all_tool_schemas()
        tools_schemas = built_in_tools + mcp_tools
        logger.debug(
            f"Using {len(built_in_tools)} built-in tools + {len(mcp_tools)} MCP tools"
        )
    else:
        tools_schemas = tools
        logger.debug(f"Using {len(tools_schemas)} provided tools")
    # The Responses API expects function tools with name/description/parameters
    # at the top level, while the shared schema builders emit the Chat
    # Completions shape with those fields nested under "function". Convert once
    # up front so every stream round sends the correct shape.
    return _convert_tools_to_responses_format(tools_schemas)


def _resolve_model_settings(
    provider: str,
    model: str,
    thinking: bool,
    reasoning_level: str | None,
) -> tuple[bool, int | None, int | None, str | None]:
    """Resolve thinking mode, token limits and reasoning level for ``model``."""
    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # model's built-in default applies (True for DeepSeek and Alibaba/Qwen,
    # which reason by default). See provider_data.PROVIDER_INFO.
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
    # the model's built-in default (from PROVIDER_INFO). None means the API's
    # own default applies.
    reasoning_level = reasoning_level or load_reasoning_level(provider, model)
    if reasoning_level is None:
        reasoning_level = get_default_reasoning_level_from_provider(provider, model)
    return thinking, max_output_tokens, max_input_tokens, reasoning_level


def _validate_stream_result(
    responses_in_server: bool,
    stream_response_id: str | None,
    full_content: str,
    tool_calls: list[dict[str, Any]] | None,
    model: str,
) -> None:
    """Raise a clear error when a server-side response came back empty."""
    if (
        responses_in_server
        and stream_response_id is None
        and not full_content
        and not tool_calls
    ):
        raise RuntimeError(
            f"The Responses API returned an empty response for model "
            f"'{model}'. The model may not be supported by this "
            f"endpoint."
        )


def _handle_not_found_error(
    e: Exception,
    base_url: str | None,
    model: str,
    response_id: str | None,
    console: Console,
) -> None:
    """Explain NotFoundError (unknown model / expired conversation) and re-raise."""
    message = str(e).lower()
    if "model not exist" in message or "model not found" in message:
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
    elif "previous response" in message:
        console.print(
            "[bold red]Error: Conversation state not found.[/bold red] "
            "The server no longer holds the referenced previous response "
            "(it may have expired or the conversation was reset)."
        )
        console.print(
            "[dim]Start a fresh conversation by passing "
            "previous_response_id=None.[/dim]"
        )
        logger.error(f"Previous response '{response_id}' not found: {e}")


def _handle_tool_calls(
    tool_calls: list[dict[str, Any]],
    full_content: str,
    conversation_items: list[dict[str, Any]] | None,
    tool_executor: ToolExecutor,
) -> list[dict[str, Any]] | None:
    """Record and execute tool calls, returning the updated input items."""
    # Record the assistant's tool calls in the client-side history
    # (stateless providers), so the next request re-sends the complete
    # story. Server-side providers keep the history on the server, so
    # nothing is appended client-side.
    if conversation_items is not None:
        if full_content:
            conversation_items.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": full_content}],
                }
            )
        for tc in tool_calls:
            conversation_items.append(
                {
                    "type": "function_call",
                    "call_id": tc["call_id"],
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                }
            )

    # Execute every call and send the results back as function_call_output
    # items chained to the response that produced the calls (server-side) or
    # appended to the full history (stateless).
    tool_outputs: list[dict[str, Any]] = []
    for tc in tool_calls:
        # Adapt the Responses API call shape to what the executor expects
        # (id + function{name, arguments}).
        adapted_call = {
            "id": tc["call_id"],
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            },
        }
        tool_message = tool_executor.execute_tool_call(adapted_call)
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": tc["call_id"],
                "output": tool_message["content"],
            }
        )
    if conversation_items is not None:
        conversation_items.extend(tool_outputs)
        return conversation_items
    return tool_outputs


def _finalize_conversation(
    full_content: str,
    conversation_items: list[dict[str, Any]] | None,
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int | None,
    message_count: int,
    console: Console,
    response_id: str | None,
    responses_in_server: bool,
) -> Any:
    """Assemble the final ConversationResult and print the end-of-turn reports."""
    from .conversations_api import ConversationResult

    # Record the final assistant text in the client-side history.
    if conversation_items is not None and full_content:
        conversation_items.append(
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": full_content}],
            }
        )

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
            message_count,
            console,
            label="Responses",
            input_attr="input_tokens",
            output_attr="output_tokens",
            cached_details_attr="input_tokens_details",
        )
    return ConversationResult(
        content=full_content,
        response_id=response_id if responses_in_server else None,
        message_count=message_count,
        input_items=conversation_items,
    )
