"""
Anthropic SDK client module for sending prompts through the **native**
Anthropic SDK (``client.messages.create``).

This is the counterpart of :mod:`janito.openai_client.completions_api` for the
``"Anthropic"`` API type: the same config resolution, tool loading, MCP
support, progress spinner, Enter-to-cancel, reasoning panel, used-files report
and token-usage summary, but talking to the Anthropic Messages API through the
official ``anthropic`` package instead of an OpenAI-compatible endpoint.

The ``anthropic`` package is **optional**: the API type is only accepted by
``--set api-type=Anthropic`` when the package is installed
(``provider_config.REQUIRES_BY_API_TYPE``), and this module refuses to run
without it, with an actionable install message.  Because the package may be
absent, the import happens lazily inside :func:`_create_client` (checked with
``importlib.util.find_spec``, mirroring the web-mode extra check) rather than
at module import time, so importing ``janito`` never requires ``anthropic``.

Like the Completions implementation, this module owns the conversation
history **client-side**: the Anthropic Messages API is stateless, so every
turn re-sends the full ``messages`` list (plus the top-level ``system``
parameter).  Tool calls are executed with the shared
:class:`~janito.tooling.executor.ToolExecutor` and their ``tool_result``
blocks are appended to the history before the next round, repeating until the
model emits a final text answer.  ``send_prompt`` returns the assistant text
and mutates ``previous_messages`` in place (Completions-style), so the
interactive shell treats this mode exactly like Completions.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from types import SimpleNamespace
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Import general configuration handling
from janito.general_config import (
    get_active_provider,
    get_masked_api_key,
    load_max_output_tokens,
)

# Import MCP manager
from janito.mcp_manager import get_mcp_manager

# Import provider configuration for built-in defaults
from janito.provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.changes import clear_changes
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files, reset_used_files

# Shared helpers reused from the Chat Completions implementation so all
# client modules stay in sync: runtime config resolution, token formatting,
# the progress spinner / Enter-to-cancel runner and the request-cancelled
# signal.
from .completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    format_tokens,
    resolve_runtime_config,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


def _create_client(base_url: str | None, api_key: str) -> Any:
    """Create the native Anthropic SDK client, guarding the optional package.

    The ``anthropic`` package is optional (see
    ``provider_config.REQUIRES_BY_API_TYPE``), so its availability is checked
    explicitly with ``importlib.util.find_spec`` (mirroring the web-mode extra
    check) and the import happens lazily -- importing ``janito`` never
    requires ``anthropic``.

    Args:
        base_url: The native-SDK base URL (from the provider's
            ``endpoint_by_api_type`` map or a config endpoint override).
        api_key: The API key from the auth store.

    Returns:
        An ``anthropic.Anthropic`` client instance.

    Raises:
        RuntimeError: If the ``anthropic`` package is not installed, with an
            actionable install message.
    """
    if importlib.util.find_spec("anthropic") is None:
        raise RuntimeError(
            "API type 'Anthropic' requires the optional 'anthropic' package, "
            "which is not installed. Install it with: pip install anthropic"
        )
    from anthropic import Anthropic

    return Anthropic(api_key=api_key, base_url=base_url)


def _convert_tools_to_anthropic_format(
    tools_schemas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Chat Completions tool schemas to the Anthropic tools format.

    The shared schema builders (``get_function_schema`` and the MCP tool
    conversion in ``mcp_manager._convert_tool_to_openai``) emit the Chat
    Completions shape with ``name``/``description``/``parameters`` nested
    under ``function``::

        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}

    The Anthropic Messages API expects ``name``/``description``/``input_schema``
    at the **top level** (``input_schema`` being the JSON-Schema of the
    parameters)::

        {"name": ..., "description": ..., "input_schema": {"type": "object", "properties": ..., "required": ...}}

    Args:
        tools_schemas: Tool schemas in Chat Completions format

    Returns:
        The same tools in Anthropic Messages format
    """
    converted = []
    for schema in tools_schemas:
        function = schema.get("function", schema)
        converted.append(
            {
                "name": function.get("name"),
                "description": function.get("description", ""),
                "input_schema": function.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        )
    return converted


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming Anthropic Messages response and assemble its parts.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info)``
    where ``tool_use_blocks`` is a list of ``{"id", "name", "input"}`` dicts
    (``input`` is the parsed JSON argument object) and ``usage_info`` is a
    ``SimpleNamespace`` with ``total_tokens``/``input_tokens``/``output_tokens``
    (``None`` when the API reported no usage).

    The Anthropic Messages API streams typed events; blocks (text, thinking,
    tool_use) arrive as ``content_block_start`` / ``content_block_delta`` /
    ``content_block_stop`` triples, so each block is assembled per index and
    flushed when it stops.  ``message_stop`` is the terminal event.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next event arrives.
    """
    collected_content: list[str] = []
    collected_reasoning: list[str] = []
    tool_use_blocks: list[dict[str, Any]] = []
    # index -> {type, text, id, name, json} while a block is in flight
    blocks: dict[int, dict[str, Any]] = {}
    input_tokens = None
    output_tokens = None
    events_seen = 0

    for event in stream:
        events_seen += 1
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next event arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break

        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            message = getattr(event, "message", None)
            if message is not None:
                usage = getattr(message, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "input_tokens", None)
        elif event_type == "content_block_start":
            index = getattr(event, "index", None)
            if index is None:
                continue
            content_block = getattr(event, "content_block", None)
            blocks[index] = {
                "type": getattr(content_block, "type", None),
                "text": "",
                "id": getattr(content_block, "id", None),
                "name": getattr(content_block, "name", None),
                "json": "",
            }
        elif event_type == "content_block_delta":
            index = getattr(event, "index", None)
            block = blocks.get(index)
            if block is None:
                continue
            delta = getattr(event, "delta", None)
            if delta is None:
                continue
            delta_type = getattr(delta, "type", None)
            if delta_type == "text_delta":
                block["text"] += getattr(delta, "text", "") or ""
            elif delta_type == "thinking_delta":
                block["text"] += getattr(delta, "thinking", "") or ""
            elif delta_type == "input_json_delta":
                block["json"] += getattr(delta, "partial_json", "") or ""
        elif event_type == "content_block_stop":
            index = getattr(event, "index", None)
            block = blocks.pop(index, None)
            if block is None:
                continue
            if block["type"] == "text":
                collected_content.append(block["text"])
            elif block["type"] == "thinking":
                if block["text"]:
                    collected_reasoning.append(block["text"])
            elif block["type"] == "tool_use":
                try:
                    parsed = json.loads(block["json"]) if block["json"].strip() else {}
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Anthropic tool-use arguments")
                    parsed = {}
                tool_use_blocks.append(
                    {
                        "id": block["id"],
                        "name": block["name"],
                        "input": parsed,
                    }
                )
        elif event_type == "message_delta":
            usage = getattr(event, "usage", None)
            if usage is not None:
                output_tokens = getattr(usage, "output_tokens", None)
        elif event_type == "message_stop":
            # Terminal event: the response is fully consumed.
            break
        elif event_type == "error":
            error = getattr(event, "error", None)
            if isinstance(error, dict):
                message = error.get("message")
            else:
                message = getattr(error, "message", None)
            raise RuntimeError(message or "Anthropic API error")

    full_content = "".join(collected_content)
    reasoning_content = "".join(collected_reasoning) if collected_reasoning else None
    # A healthy stream always ends with message_stop; a stream with zero
    # events means the API failed before producing anything. Fail loudly
    # instead of returning an empty answer. An Enter-to-cancel short-circuit
    # must not be treated as an empty stream.
    if events_seen == 0 and (cancel_event is None or not cancel_event.is_set()):
        raise RuntimeError(
            "The Anthropic API returned no stream events (empty response)."
        )
    usage_info = None
    if input_tokens is not None or output_tokens is not None:
        usage_info = SimpleNamespace(
            total_tokens=(input_tokens or 0) + (output_tokens or 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return full_content, reasoning_content, tool_use_blocks, usage_info


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming Anthropic Messages call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info)``.
    Tool schemas are attached here (mirroring ``completions_api._stream_response``);
    the caller builds the remaining kwargs per round.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    if tools_schemas:
        logger.debug(
            f"Calling Anthropic Messages API (streaming) with {len(tools_schemas)} tools"
        )
        stream = client.messages.create(**call_kwargs, tools=tools_schemas)
    else:
        logger.debug("Calling Anthropic Messages API (streaming) without tools")
        stream = client.messages.create(**call_kwargs)

    try:
        return _consume_stream(stream, cancel_event=cancel_event)
    finally:
        # Abort the underlying HTTP stream when the user pressed Enter so the
        # connection is released promptly instead of streaming to completion.
        if cancel_event is not None and cancel_event.is_set():
            stream.close()


def send_prompt(
    prompt: str,
    verbose: bool = False,
    previous_messages: list[dict[str, Any]] | None = None,
    instructions: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    use_mcp: bool = True,
    thinking: bool = False,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
) -> str:
    """Send a prompt through the native Anthropic SDK and return the answer.

    Mirrors :func:`completions_api.send_prompt` (same config resolution, tool
    loading, spinner, reasoning panel, used-files report and usage summary)
    but targets the Anthropic Messages API.  The conversation history is owned
    **client-side**: ``previous_messages`` is mutated in place (user and
    assistant turns are appended) so the interactive shell's history keeps
    growing, exactly like Completions mode.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation
            context (mutated in place). A leading ``"system"``-role message is
            extracted and sent as the top-level Anthropic ``system`` parameter.
        instructions: System instructions for the conversation (sent as the
            top-level Anthropic ``system`` parameter). When ``None``, a
            leading ``"system"``-role message in ``previous_messages`` is used.
        tools: Optional list of tool schemas to pass. If None, uses all
            available tools. If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: Accepted for signature parity with the other clients. The
            native Anthropic extended-thinking mode is not wired yet; thinking
            text is still displayed when the model streams it.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Accepted for signature parity with the other clients.
            The native Anthropic SDK does not use ``reasoning_effort``.

    Returns:
        The assistant's final text (after any tool-call rounds).

    Raises:
        RuntimeError: If the ``anthropic`` package is not installed.
    """
    logger.info("Sending prompt to Anthropic API (native SDK)")
    # Remove any changes log from a previous prompt so ./janito/changes.jsonl
    # only describes the changes made while handling the current prompt.
    clear_changes()
    # Clear the in-process used-files tracker so the end-of-prompt
    # "Used files" report only describes files touched while handling the
    # *current* prompt instead of accumulating across the whole session.
    reset_used_files()
    # This module is the "Anthropic" API type, so endpoint resolution picks
    # the native-SDK base URL from the provider's endpoint_by_api_type map.
    base_url, api_key, model = resolve_runtime_config(
        cli_model, cli_provider, cli_api_type="Anthropic"
    )
    client = _create_client(base_url, api_key)

    logger.debug(f"Anthropic client created with base_url={base_url}")

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

    # The Anthropic Messages API expects name/description/input_schema at the
    # top level, while the shared schema builders emit the Chat Completions
    # shape (nested under "function"). Convert once up front.
    tools_schemas = _convert_tools_to_anthropic_format(tools_schemas)

    logger.debug(f"Using {len(tools_schemas)} tools total")

    provider = cli_provider or get_active_provider()

    # Max output tokens: the Anthropic Messages API requires max_tokens, so
    # the resolved value (config > provider built-in default > 100k) is always
    # passed.
    max_output_tokens = load_max_output_tokens(provider)
    if max_output_tokens is None:
        max_output_tokens = get_default_max_output_tokens_from_provider(provider)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the provider's built-in max input tokens (context window) for the
    # usage summary display.
    max_input_tokens = get_default_max_input_tokens_from_provider(provider)

    console = Console()

    # Print model and backend info only in verbose mode
    if verbose:
        backend = base_url if base_url else "https://api.anthropic.com"
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

    # Build the conversation. The Anthropic Messages API takes the system
    # prompt as a top-level `system` parameter (not a "system"-role message),
    # so system-role messages are extracted from the history and the request
    # payload filters them out. The in-place history list keeps them so the
    # shell's messages_history stays intact.
    messages = previous_messages if previous_messages is not None else []
    system = instructions
    system_messages = [
        m for m in messages if m.get("role") == "system" and m.get("content")
    ]
    if system is None and system_messages:
        system = "\n\n".join(str(m.get("content")) for m in system_messages)

    def _api_messages() -> list[dict[str, Any]]:
        return [m for m in messages if m.get("role") != "system"]

    # NOTE: check `is not None` (not truthiness). An empty list is a valid,
    # caller-owned history (e.g. after a restart or with --no-system-prompt);
    # using a truthy check would replace it with a new local list and the
    # appended messages would never propagate back to the caller.
    messages.append({"role": "user", "content": prompt})

    logger.debug(f"Starting message loop with {len(messages)} messages")

    while True:
        # Build the base call parameters. system is a top-level parameter that
        # may be sent on every round (the Messages API is stateless and the
        # full history is re-sent each time).
        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": _api_messages(),
            "max_tokens": max_output_tokens,
        }
        if system:
            call_kwargs["system"] = system

        # ------ Streaming API call ------
        call_kwargs["stream"] = True

        # Consume the full stream under a progress bar. The blocking work
        # (connection setup + full response generation) runs in a worker thread
        # via _run_with_progress_bar while the main thread drives the spinner,
        # mirroring the completions_api behaviour.
        try:
            (
                full_content,
                reasoning_content,
                tool_use_blocks,
                usage_info,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except Exception as e:
            # The anthropic SDK raises its own exception types; format the
            # common authentication failure with the same actionable details
            # as the OpenAI clients (the exception is always re-raised).
            if getattr(e, "status_code", None) == 401:
                masked_key = get_masked_api_key(api_key)
                console.print(
                    "[bold red]Error: Authentication failed (invalid API key).[/bold red]"
                )
                console.print(f"  Provider: [bold]{provider}[/bold]")
                console.print(f"  Model:    [bold]{model}[/bold]")
                console.print(f"  API URL:  [bold]{base_url}[/bold]")
                console.print(f"  API Key:  [bold]{masked_key}[/bold]")
                console.print(
                    f"[dim]Please verify your API key for the '{provider}' provider "
                    f"and try again.[/dim]"
                )
                logger.error(
                    f"Authentication failed - provider: {provider}, model: {model}, "
                    f"api_url: {base_url}, api_key: {masked_key}: {e}"
                )
            raise

        logger.debug("Anthropic Messages streaming response completed")
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

        # Display the assembled response using rich markdown
        if full_content:
            console.print(Markdown(full_content))

        # Check if the model wants to call tools
        if tool_use_blocks:
            # Record the assistant's message with its content blocks (text +
            # tool_use) in the client-side history, then execute every call
            # and send the results back as tool_result blocks before looping
            # to get the final answer.
            assistant_blocks: list[dict[str, Any]] = []
            if full_content:
                assistant_blocks.append({"type": "text", "text": full_content})
            for tc in tool_use_blocks:
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    }
                )
            messages.append({"role": "assistant", "content": assistant_blocks})

            tool_outputs: list[dict[str, Any]] = []
            for tc in tool_use_blocks:
                # Adapt the Anthropic tool-use shape to what the executor
                # expects (id + function{name, arguments}).
                adapted_call = {
                    "id": tc["id"],
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["input"]),
                    },
                }
                tool_message = tool_executor.execute_tool_call(adapted_call)
                tool_outputs.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": tool_message["content"],
                    }
                )
            messages.append({"role": "user", "content": tool_outputs})
            continue
        else:
            # No more tool calls, return the final response. Record the final
            # assistant text in the client-side history.
            messages.append({"role": "assistant", "content": full_content})

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
                parts.append(f"Messages: {len(messages)}")

                token_text = Text(f"=== {' | '.join(parts)} ===")
                token_text.stylize("white on magenta")
                console.print(token_text, highlight=False)
                logger.info(
                    f"Request completed: total={total_tokens} tokens "
                    f"(in={input_tokens}, out={output_tokens}, "
                    f"max={max_output_tokens}), {len(messages)} messages"
                )
            return full_content


__all__ = [
    "RequestCancelled",
    "send_prompt",
]
