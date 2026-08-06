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
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import AuthenticationError, NotFoundError, OpenAI
from rich.console import Console
from rich.markdown import Markdown

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_config_value,
    get_masked_api_key,
    load_max_output_tokens,
    load_reasoning_level,
)

# Import MCP manager
from janito.mcp_manager import get_mcp_manager

# Import provider configuration for built-in defaults
from janito.provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_reasoning_level_from_provider,
    get_default_thinking_from_provider,
    get_responses_in_server_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.changes import clear_changes
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files, reset_used_files

# Shared helpers reused from the Chat Completions implementation so both
# modules stay in sync: runtime config resolution, token formatting, the
# progress spinner / Enter-to-cancel runner and the request-cancelled signal.
from .completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    format_tokens,
    resolve_runtime_config,
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


def _convert_tools_to_responses_format(
    tools_schemas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Chat Completions tool schemas to the Responses API format.

    The shared schema builders (``get_function_schema`` and the MCP tool
    conversion in ``mcp_manager._convert_tool_to_openai``) emit the Chat
    Completions shape with ``name``/``description``/``parameters`` nested
    under ``function``::

        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}

    The Responses API expects those fields at the **top level**::

        {"type": "function", "name": ..., "description": ..., "parameters": ...}

    Without this conversion ``client.responses.create(tools=...)`` fails with
    ``tools[0]: missing field 'name'``.

    Args:
        tools_schemas: Tool schemas in Chat Completions format

    Returns:
        The same tools in Responses API format
    """
    converted = []
    for schema in tools_schemas:
        function = schema.get("function", schema)
        converted.append(
            {
                "type": "function",
                "name": function.get("name"),
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {}),
            }
        )
    return converted


def _consume_response_stream(stream, cancel_event=None):
    """Consume a streaming Responses API response and assemble its parts.

    Returns ``(full_content, reasoning_content, tool_calls, usage_info,
    response_id)`` where ``tool_calls`` is a list of
    ``{"call_id", "name", "arguments"}`` dicts. Unlike Chat Completions
    (which splits tool calls across chunks indexed by position), the
    Responses API emits a ``response.output_item.done`` event per finished
    output item, so each call carries its stable ``call_id``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next event arrives.
    """
    collected_content: list[str] = []
    collected_reasoning: list[str] = []
    tool_calls: list[dict[str, str]] = []
    # function_call arguments may arrive split across many
    # ``response.function_call_arguments.delta`` events; keep the partial
    # strings per output item in case the final item omits them.
    partial_arguments: dict[str, str] = {}
    usage_info = None
    response_id = None

    for event in stream:
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next event arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break

        event_type = event.type

        # The response id is the handle used to chain the next turn; it is
        # known as soon as the server creates (or completes) the response.
        if event_type == "response.created":
            response_id = event.response.id
        elif event_type == "response.completed":
            response_id = event.response.id
            # Usage is delivered on the final event when include=["usage"].
            if event.response.usage:
                usage_info = event.response.usage
        elif event_type == "response.failed":
            error = event.response.error
            message = error.message if error and error.message else "Response failed"
            raise RuntimeError(message)

        # Assistant text
        elif event_type == "response.output_text.delta":
            if event.delta:
                collected_content.append(event.delta)

        # Reasoning / thinking text (models that expose it; otherwise empty)
        elif event_type in (
            "response.reasoning_text.delta",
            "response.reasoning_summary_text.delta",
        ):
            if event.delta:
                collected_reasoning.append(event.delta)

        # Tool-call arguments, assembled per output item
        elif event_type == "response.function_call_arguments.delta":
            item_id = event.item_id
            partial_arguments[item_id] = partial_arguments.get(item_id, "") + (
                event.delta or ""
            )
        elif event_type == "response.function_call_arguments.done":
            partial_arguments[event.item_id] = event.arguments or ""
        elif event_type == "response.output_item.done":
            item = event.item
            if getattr(item, "type", None) == "function_call":
                tool_calls.append(
                    {
                        "call_id": item.call_id,
                        "name": item.name,
                        "arguments": item.arguments
                        or partial_arguments.get(item.id, ""),
                    }
                )

    full_content = "".join(collected_content)
    reasoning_content = "".join(collected_reasoning) if collected_reasoning else None
    return full_content, reasoning_content, tool_calls, usage_info, response_id


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming Responses API call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls, usage_info,
    response_id)``. Tool schemas are attached here (mirroring
    ``completions_api._stream_response``); the caller builds the remaining
    kwargs per round.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    if tools_schemas:
        logger.debug(
            f"Calling Responses API (streaming) with {len(tools_schemas)} tools"
        )
        stream = client.responses.create(
            **call_kwargs,
            tools=tools_schemas,
            tool_choice="auto",
        )
    else:
        logger.debug("Calling Responses API (streaming) without tools")
        stream = client.responses.create(**call_kwargs)

    try:
        return _consume_response_stream(stream, cancel_event=cancel_event)
    finally:
        # Abort the underlying HTTP stream when the user pressed Enter so the
        # connection is released promptly instead of streaming to completion.
        if cancel_event is not None and cancel_event.is_set():
            stream.close()


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

    # Initialize MCP manager and load services if enabled
    mcp_manager = None
    if use_mcp:
        mcp_manager = get_mcp_manager()
        try:
            mcp_manager.load_services()
            mcp_tools = mcp_manager.get_all_tools()
            logger.info(
                f"Loaded {len(mcp_tools)} MCP tools from {len(mcp_manager.connected_services)} services"
            )
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}")
            mcp_tools = []
    else:
        mcp_tools = []

    # Tool executor routes tool calls to the MCP manager or the built-in
    # registry and tracks usage/used-files/changes around each call.
    tool_executor = ToolExecutor(mcp_manager)

    # Get available tools if not explicitly provided
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

    # The Responses API expects function tools with name/description/parameters
    # at the top level, while the shared schema builders (get_function_schema,
    # MCP conversion) emit the Chat Completions shape with those fields nested
    # under "function". Convert once up front so every stream round sends the
    # correct shape.
    tools_schemas = _convert_tools_to_responses_format(tools_schemas)

    logger.debug(f"Using {len(tools_schemas)} tools total")

    # Load max output tokens from general config if set
    provider = cli_provider or get_active_provider()

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

    # Check for preserve_thinking in config
    preserve_thinking = get_config_value("preserve_thinking")
    if preserve_thinking is not None:
        logger.debug(f"Using preserve_thinking from config: {preserve_thinking}")

    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "api.openai.com"
        from rich.text import Text

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

    # Conversation-state model depends on the provider: some Responses
    # endpoints (e.g. OpenAI) keep the conversation server-side and chain
    # turns with previous_response_id; others (e.g. DeepSeek's /responses,
    # which is stateless) cannot resolve a previous response id, so the
    # client tracks the full conversation as Responses input items and
    # re-sends them on every request (like Chat Completions).
    responses_in_server = get_responses_in_server_from_provider(provider)
    if responses_in_server:
        response_id = previous_response_id
        conversation_items: list[dict[str, Any]] | None = None
        # The first round sends the raw prompt; tool-call rounds send the
        # function_call_output items chained to the previous response.
        input_items: str | list[dict[str, Any]] = prompt
    else:
        # Stateless: never chain with previous_response_id; each request
        # re-sends the entire conversation as input items.
        response_id = None
        conversation_items = list(previous_items or [])
        # Fold the system instructions into the history on the first turn so
        # the stateless server receives the full context on every request.
        if not conversation_items and instructions:
            conversation_items.append(
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                }
            )
        conversation_items.append(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        )
        input_items = conversation_items
    message_count = 1

    while True:
        # Build the base call parameters
        call_kwargs: dict[str, Any] = {
            "model": model,
            "input": input_items,
            "temperature": 1.0,
        }

        # Add max_output_tokens if max output tokens is set in config
        if max_output_tokens is not None:
            call_kwargs["max_output_tokens"] = max_output_tokens

        # Pass the reasoning level (reasoning_effort) when resolved (from
        # --reasoning-level, per-provider config, or the built-in default).
        if reasoning_level:
            call_kwargs["reasoning"] = {"effort": reasoning_level}

        # Pass preserve_thinking in extra_body if defined in config
        if preserve_thinking is not None:
            if "extra_body" not in call_kwargs:
                call_kwargs["extra_body"] = {}
            call_kwargs["extra_body"]["preserve_thinking"] = preserve_thinking

        # Pass enable_thinking in extra_body if thinking flag is set
        if thinking:
            if "extra_body" not in call_kwargs:
                call_kwargs["extra_body"] = {}
            call_kwargs["extra_body"]["enable_thinking"] = True

        # ------ Streaming API call ------
        # Stream the response; include=["usage"] makes the final
        # response.completed event carry the usage statistics.
        call_kwargs["stream"] = True
        call_kwargs["include"] = ["usage"]

        # Chain to the previous server-side response when continuing a
        # server-side conversation (multi-turn or tool-call round). Stateless
        # providers never chain: the full history is already in ``input`` and
        # the system instructions were folded into it on the first turn.
        if response_id is not None:
            call_kwargs["previous_response_id"] = response_id
        elif responses_in_server and instructions:
            # First turn of a server-side conversation: system instructions
            # are only sent here; the server folds them into the stored
            # conversation.
            call_kwargs["instructions"] = instructions

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
        except NotFoundError as e:
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
            raise
        except AuthenticationError as e:
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
            raise

        logger.debug("Responses API streaming response completed")
        if reasoning_content:
            from rich.panel import Panel

            console.print(
                Panel(
                    Markdown(reasoning_content),
                    title="[bold cyan]\U0001f4ad Reasoning[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
            logger.debug("Reasoning content displayed")

        # Display the assembled response using rich markdown
        if full_content:
            console.print(Markdown(full_content))

        # Check if the model wants to call tools
        if tool_calls:
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

            # Execute every call and send the results back as
            # function_call_output items chained to the response that produced
            # the calls (server-side) or appended to the full history
            # (stateless).
            tool_outputs: list[dict[str, Any]] = []
            for tc in tool_calls:
                # Adapt the Responses API call shape to what the executor
                # expects (id + function{name, arguments}).
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
            # Continue the loop: the next round sends the tool outputs chained
            # to the response that requested them (response_id was updated by
            # the stream consumer above), or the full accumulated history for
            # stateless providers.
            if conversation_items is not None:
                conversation_items.extend(tool_outputs)
                input_items = conversation_items
            else:
                input_items = tool_outputs
            message_count += 1
            continue
        else:
            # No more tool calls, return the final response. Server-side: the
            # assistant message lives on the server and the caller only needs
            # the response id to chain the next turn. Stateless: append the
            # final assistant text to the client-side history and hand the
            # full items back so the caller can re-send them next turn.

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
                total_tokens = getattr(usage_info, "total_tokens", None)
                input_tokens = getattr(usage_info, "input_tokens", None)
                output_tokens = getattr(usage_info, "output_tokens", None)
                cached_tokens = None
                details = getattr(usage_info, "input_tokens_details", None)
                if details:
                    cached_tokens = getattr(details, "cached_tokens", None)

                from rich.text import Text

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
                parts.append(f"Responses: {message_count}")

                token_text = Text(f"=== {' | '.join(parts)} ===")
                token_text.stylize("white on magenta")
                console.print(token_text, highlight=False)
                logger.info(
                    f"Request completed: total={total_tokens} tokens "
                    f"(in={input_tokens}, out={output_tokens}, "
                    f"cached={cached_tokens}, max={max_output_tokens}), "
                    f"{message_count} responses"
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
