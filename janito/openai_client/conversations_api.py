"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints using
the Responses API (``client.responses.create``) with server-side conversation
state.

This module mirrors :mod:`janito.openai_client.completions_api` (same config
resolution, tool loading, MCP support, progress spinner, Enter-to-cancel,
reasoning panel, used-files report and token-usage summary), but targets the
Responses API instead of the Chat Completions API.

The important difference is **who owns the conversation history**. The
Completions implementation stores and updates a ``messages`` list on the
client side. This module delegates to the server: the Responses API keeps the
conversation server-side and turns are chained with ``previous_response_id``::

    result = send_prompt("First question")
    result = send_prompt("Follow-up", previous_response_id=result.response_id)

Tool calls work the same way: the model's ``function_call`` output items are
executed and the results are sent back as ``function_call_output`` input items
chained to the response that produced the calls, repeating until the model
emits a final text answer. Only the final ``response_id`` needs to be kept by
the caller.

**Stateless endpoints.** Some providers' ``/responses`` endpoint is stateless
(``responses_in_server`` is ``False`` in ``PROVIDER_INFO``, e.g. DeepSeek):
it cannot resolve a ``previous_response_id`` and rejects tool outputs that
reference it. For those providers the client falls back to the Completions
model of ownership: the full conversation is tracked as Responses input items
(``ConversationResult.input_items``) and re-sent on every request via
``previous_items``, with the system instructions folded into the first turn.

The Responses API stream handling lives in
:mod:`janito.openai_client.responses_stream` and the shared client helpers in
:mod:`janito.openai_client.client_support`; both are re-exported here so
existing ``conversations_api.<name>`` references keep working.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import AuthenticationError, NotFoundError, OpenAI
from rich.console import Console

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_config_value,
    load_max_output_tokens,
    load_reasoning_level,
)

# Import provider configuration for built-in defaults
from janito.provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.changes import clear_changes
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files, reset_used_files

# Shared client helpers (MCP loading, Rich console output, auth-error
# explainer) and the Responses API stream consumer.  Names that are only
# re-exported for backward compatibility are marked ``noqa: F401``.
from .client_support import (  # noqa: F401 (re-exported for backward compat)
    _display_content,
    _display_reasoning,
    _display_usage,
    _handle_auth_error,
    _load_mcp,
    _print_verbose_info,
    format_tokens,
)

# Shared helpers reused from the Chat Completions implementation so both
# modules stay in sync: runtime config resolution, the progress spinner /
# Enter-to-cancel runner and the request-cancelled signal.
from .completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    resolve_runtime_config,
)
from .responses_state import _build_call_kwargs, _init_conversation_state
from .responses_stream import (  # noqa: F401 (re-exported for backward compat)
    _consume_response_stream,
    _convert_tools_to_responses_format,
    _handle_call_arguments,
    _handle_completion_event,
    _handle_output_item,
    _handle_stream_event,
    _handle_text_delta,
    _handle_untyped_error,
    _raise_failed_error,
    _stream_response,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ConversationResult:
    """Outcome of one ``send_prompt`` turn against the Responses API.

    Attributes:
        content: The assistant's final text (after any tool-call rounds).
        response_id: The server-side id of the final response. For providers
            that keep the conversation server-side (``responses_in_server``
            True), pass it as ``previous_response_id`` to the next
            ``send_prompt`` call to continue the conversation. For stateless
            providers (``responses_in_server`` False) this is always ``None``
            and the history is carried client-side in ``input_items`` instead.
        message_count: Number of responses chained during this turn (1 +
            number of tool-call rounds).
        input_items: The full conversation as Responses input items, only for
            stateless providers (``responses_in_server`` False). Pass it back
            as ``previous_items`` to the next ``send_prompt`` call so the
            entire history is re-sent (the server keeps no state). ``None``
            for server-side providers, which chain with ``response_id``.
    """

    content: str
    response_id: str | None
    message_count: int = 1
    input_items: list[dict[str, Any]] | None = None


def get_env_config() -> tuple[str | None, str, str]:
    """Backward-compatible alias for :func:`resolve_runtime_config`.

    Mirrors ``completions_api.get_env_config``; resolves configuration from
    auth/config without using environment variables.
    """
    return resolve_runtime_config()


def send_prompt(
    prompt: str,
    verbose: bool = False,
    previous_response_id: str | None = None,
    previous_items: list[dict[str, Any]] | None = None,
    instructions: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    use_mcp: bool = True,
    thinking: bool = False,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
) -> ConversationResult:
    """Send a prompt to the Responses API and return the final answer.

    Mirrors :func:`completions_api.send_prompt` (same config resolution, tool
    loading, spinner, reasoning panel, used-files report and usage summary)
    but the conversation history lives **server-side**: the client neither
    stores nor updates a ``messages`` list. Multi-turn conversations chain
    responses with ``previous_response_id``; tool-call rounds are chained
    internally the same way, so only the final ``response_id`` matters to the
    caller.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_response_id: The server-side id of the previous response to
            continue from (``None`` for a fresh conversation). Obtained from
            the ``response_id`` of the previous ``ConversationResult``. Only
            used for providers whose Responses API keeps server-side state
            (``responses_in_server`` True); ignored for stateless providers.
        previous_items: The full conversation as Responses input items
            (obtained from the previous result's ``input_items``). Only used
            for stateless providers (``responses_in_server`` False), which
            cannot resolve a ``previous_response_id`` and must re-send the
            entire history on every request. ``None`` for a fresh
            conversation.
        instructions: System instructions for the conversation. For server-side
            providers they are only sent on the first turn (the server folds
            them into the stored conversation); for stateless providers they
            are folded into the client-side history on the first turn so every
            request carries the full context.
        tools: Optional list of tool schemas to pass. If None, uses all
            available tools. If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: If True, enable thinking mode (extra_body=
            {'enable_thinking': True}). When False (default), falls back to
            the provider's built-in default.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Reasoning depth passed via ``--reasoning-level``
            (overrides the provider's configured value and built-in default).
            Sent to the API as ``reasoning_effort`` under the ``reasoning``
            parameter.

    Returns:
        ConversationResult: the final assistant text plus, depending on the
        provider's conversation model, the server-side response id (to chain
        the next turn with ``previous_response_id``) or the full client-side
        input items (to re-send with ``previous_items``).
    """
    logger.info("Sending prompt to Responses API")
    # Remove any changes log from a previous prompt so ./janito/changes.jsonl
    # only describes the changes made while handling the current prompt.
    clear_changes()
    # Clear the in-process used-files tracker so the end-of-prompt
    # "Used files" report only describes files touched while handling the
    # *current* prompt instead of accumulating across the whole session.
    reset_used_files()
    base_url, api_key, model = resolve_runtime_config(cli_model, cli_provider)

    # Create OpenAI client - base_url can be None for standard OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    logger.debug(f"OpenAI client created with base_url={base_url}")

    # Initialize MCP manager and load services if enabled; the tool executor
    # routes tool calls to the MCP manager or the built-in registry and tracks
    # usage/used-files/changes around each call.
    mcp_manager, mcp_tools = _load_mcp(use_mcp)
    tool_executor = ToolExecutor(mcp_manager)
    tools_schemas = _resolve_tools(tools, mcp_tools)

    logger.debug(f"Using {len(tools_schemas)} tools total")

    provider = cli_provider or get_active_provider()
    (
        thinking,
        max_output_tokens,
        max_input_tokens,
        reasoning_level,
    ) = _resolve_model_settings(provider, thinking, reasoning_level)
    preserve_thinking = get_config_value("preserve_thinking")
    if preserve_thinking is not None:
        logger.debug(f"Using preserve_thinking from config: {preserve_thinking}")

    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        _print_verbose_info(console, base_url, model, mcp_manager, "api.openai.com")

    # Conversation-state model depends on the provider: some Responses
    # endpoints (e.g. OpenAI) keep the conversation server-side and chain
    # turns with previous_response_id; others (e.g. DeepSeek's /responses,
    # which is stateless) cannot resolve a previous response id, so the
    # client tracks the full conversation as Responses input items and
    # re-sends them on every request (like Chat Completions).
    (
        responses_in_server,
        response_id,
        conversation_items,
        input_items,
    ) = _init_conversation_state(
        provider, previous_response_id, previous_items, instructions, prompt
    )
    message_count = 1

    while True:
        # Build the base call parameters
        call_kwargs = _build_call_kwargs(
            model,
            input_items,
            max_output_tokens,
            reasoning_level,
            preserve_thinking,
            thinking,
            response_id,
            responses_in_server,
            instructions,
        )

        # Consume the full stream under a progress bar. The blocking work
        # (connection setup + full response generation) runs in a worker thread
        # via _run_with_progress_bar while the main thread drives the spinner,
        # mirroring the completions_api behaviour.
        try:
            (
                full_content,
                reasoning_content,
                tool_calls,
                usage_info,
                stream_response_id,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
            # Only server-side conversations chain with the returned id;
            # stateless providers never send previous_response_id.
            if responses_in_server:
                response_id = stream_response_id
            # Safety net: a server-side provider that never reported a
            # response id and produced neither content nor tool calls means
            # the request failed without a proper error event. Raise a clear
            # error naming the model instead of returning an empty result.
            _validate_stream_result(
                responses_in_server, stream_response_id, full_content, tool_calls, model
            )
        except NotFoundError as e:
            _handle_not_found_error(e, base_url, model, response_id, console)
            raise
        except AuthenticationError as e:
            _handle_auth_error(e, cli_provider, api_key, base_url, model, console)
            raise

        logger.debug("Responses API streaming response completed")
        _display_reasoning(reasoning_content, console)

        # Display the assembled response using rich markdown
        _display_content(full_content, console)

        # Check if the model wants to call tools
        if tool_calls:
            # Record the assistant's tool calls in the client-side history
            # (stateless providers) and execute every call, sending the results
            # back as function_call_output items chained to the response that
            # produced the calls (server-side) or appended to the full history
            # (stateless). Then continue the loop.
            input_items = _handle_tool_calls(
                tool_calls, full_content, conversation_items, tool_executor
            )
            message_count += 1
            continue

        # No more tool calls, return the final response. Server-side: the
        # assistant message lives on the server and the caller only needs the
        # response id to chain the next turn. Stateless: append the final
        # assistant text to the client-side history and hand the full items
        # back so the caller can re-send them next turn.
        return _finalize_conversation(
            full_content,
            conversation_items,
            usage_info,
            max_input_tokens,
            max_output_tokens,
            message_count,
            console,
            response_id,
            responses_in_server,
        )


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
    thinking: bool,
    reasoning_level: str | None,
) -> tuple[bool, int | None, int | None, str | None]:
    """Resolve thinking mode, token limits and reasoning level."""
    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # provider's built-in default applies (True for DeepSeek and Alibaba/Qwen,
    # which reason by default). See provider_config.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider)
    max_output_tokens = load_max_output_tokens(provider)
    if max_output_tokens is None:
        # Fall back to the provider's built-in default (from PROVIDER_INFO),
        # then to a global default of 100k tokens.
        max_output_tokens = get_default_max_output_tokens_from_provider(provider)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the provider's built-in max input tokens (context window) for the
    # usage summary display.
    max_input_tokens = get_default_max_input_tokens_from_provider(provider)

    # Reasoning level (reasoning_effort): --reasoning-level CLI arg, then the
    # provider's configured value (--set reasoning-level=...), and finally the
    # provider's built-in default (from PROVIDER_INFO). None means the API's
    # own default applies.
    reasoning_level = reasoning_level or load_reasoning_level(provider)
    if reasoning_level is None:
        reasoning_level = get_default_reasoning_level_from_provider(provider)
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
) -> ConversationResult:
    """Assemble the final ConversationResult and print the end-of-turn reports."""
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


__all__ = [
    "ConversationResult",
    "RequestCancelled",
    "get_env_config",
    "resolve_runtime_config",
    "send_prompt",
]
