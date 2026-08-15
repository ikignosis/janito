"""
Anthropic SDK client module for sending prompts through the **native**
Anthropic SDK (``client.messages.create``).

This is the counterpart of :mod:`janito.openai_client.completions_api` for the
``"Anthropic"`` API type: the same config resolution, tool loading, MCP
support, progress spinner, reasoning panel, used-files report
and token-usage summary, but talking to the Anthropic Messages API through the
official ``anthropic`` package instead of an OpenAI-compatible endpoint.

The ``anthropic`` package is **optional**: the API type is only accepted by
``--set api-type=Anthropic`` when the package is installed
(``janito.providers.REQUIRES_BY_API_TYPE``), and this module refuses to run
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

The Messages API stream handling lives in
:mod:`janito.openai_client.anthropic_stream` and the shared client helpers in
:mod:`janito.openai_client.client_support`; both are re-exported here so
existing ``anthropic_api.<name>`` references keep working.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from typing import Any

from rich.console import Console

# Import general configuration handling
from janito.config_loaders import load_max_input_tokens, load_max_output_tokens

# Import provider configuration for built-in defaults
from janito.provider_accessors import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files

from .anthropic_stream import (  # noqa: F401 (re-exported for backward compat)
    _consume_stream,
    _convert_tools_to_anthropic_format,
    _handle_anthropic_event,
    _handle_content_block_delta,
    _handle_content_block_start,
    _handle_content_block_stop,
    _handle_message_delta,
    _handle_message_start,
    _parse_tool_use_block,
    _raise_anthropic_error,
    _stream_response,
)

# Shared agent-loop pipeline (see Client.send) implemented by AnthropicClient.
from .base_client import Client

# Shared client helpers (Rich console output, auth-error explainer) used by
# the module's remaining functions (finalize / error handling).
from .client_support import _display_usage, _handle_auth_error

# Shared helpers reused from the Chat Completions implementation so all
# client modules stay in sync: runtime config resolution and the progress
# spinner runner.
from .completions_api import _run_with_progress_bar, resolve_runtime_config

# Configure logger for this module
logger = logging.getLogger(__name__)


def _create_client(base_url: str | None, api_key: str) -> Any:
    """Create the native Anthropic SDK client, guarding the optional package.

    The ``anthropic`` package is optional (see
    ``janito.providers.REQUIRES_BY_API_TYPE``), so its availability is checked
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
    return AnthropicClient(
        cli_model=cli_model,
        cli_provider=cli_provider,
        reasoning_level=reasoning_level,
        use_mcp=use_mcp,
    ).send(
        prompt,
        verbose=verbose,
        previous_messages=previous_messages,
        instructions=instructions,
        tools=tools,
        thinking=thinking,
    )


class AnthropicClient(Client):
    """Native Anthropic SDK client (``client.messages.create``).

    The conversation history is owned **client-side**: ``previous_messages``
    is mutated in place (user/assistant turns are appended), exactly like
    Completions mode.  The Anthropic Messages API takes the system prompt as a
    top-level ``system`` parameter, so system-role messages are extracted from
    the history (the in-place list keeps them so the shell's history stays
    intact).  Every hook forwards to this module's globals so test
    monkeypatches keep working.
    """

    api_type = "Anthropic"
    backend_default = "https://api.anthropic.com"

    def _resolve_runtime_config(self):
        # This module is the "Anthropic" API type, so endpoint resolution
        # picks the native-SDK base URL from the endpoint_by_api_type map.
        return resolve_runtime_config(
            self.cli_model, self.cli_provider, cli_api_type="Anthropic"
        )

    def _create_sdk_client(self, base_url, api_key):
        return _create_client(base_url, api_key)

    def _create_tool_executor(self, mcp_manager):
        return ToolExecutor(mcp_manager)

    def _resolve_tools(self, tools, mcp_tools):
        return _resolve_tools(tools, mcp_tools)

    def _resolve_model_settings(self, provider, model, thinking, reasoning_level):
        # The Anthropic Messages API requires max_tokens, so the resolved
        # value (config > model built-in default > 100k) is always passed.
        # thinking / reasoning_level are accepted for signature parity but the
        # native extended-thinking mode is not wired yet.
        return (
            thinking,
            _resolve_max_output_tokens(provider, model),
            _resolve_max_input_tokens(provider, model),
            None,
        )

    def _init_conversation_state(self, prompt, provider, model, **kwargs):
        # Build the conversation. The Anthropic Messages API takes the system
        # prompt as a top-level `system` parameter (not a "system"-role
        # message), so system-role messages are extracted from the history and
        # the request payload filters them out. The in-place history list
        # keeps them so the shell's messages_history stays intact.
        previous_messages = kwargs.get("previous_messages")
        messages = previous_messages if previous_messages is not None else []
        system = _resolve_system_prompt(kwargs.get("instructions"), messages)

        # NOTE: check `is not None` (not truthiness). An empty list is a valid,
        # caller-owned history (e.g. after a restart or with
        # --no-system-prompt); using a truthy check would replace it with a new
        # local list and the appended messages would never propagate back to
        # the caller.
        messages.append({"role": "user", "content": prompt})
        return {"messages": messages, "system": system}

    def _build_call_kwargs(
        self,
        model,
        state,
        max_output_tokens,
        reasoning_level,
        preserve_thinking,
        thinking,
    ):
        # system is a top-level parameter that may be sent on every round (the
        # Messages API is stateless and the full history is re-sent each time).
        return _build_call_kwargs(
            model, state["messages"], max_output_tokens, state["system"]
        )

    def _run_stream_round(
        self,
        client,
        call_kwargs,
        tools_schemas,
        state,
        *,
        base_url,
        api_key,
        model,
        console,
    ):
        try:
            return _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except Exception as e:
            # The anthropic SDK raises its own exception types; format the
            # common authentication failure with the same actionable details
            # as the OpenAI clients (the exception is always re-raised).
            _handle_auth_error(e, self.cli_provider, api_key, base_url, model, console)
            raise

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        # Record the assistant's message with its content blocks (text +
        # tool_use) in the client-side history, then execute every call and
        # send the results back as tool_result blocks before looping to get
        # the final answer.
        _handle_tool_blocks(tool_calls, full_content, state["messages"], tool_executor)
        return state

    def _finalize(
        self,
        full_content,
        reasoning_content,
        state,
        usage_info,
        max_input_tokens,
        max_output_tokens,
        console,
    ):
        # No more tool calls, return the final response.
        return _finalize_response(
            full_content,
            state["messages"],
            usage_info,
            max_input_tokens,
            max_output_tokens,
            console,
        )


def _resolve_tools(
    tools: list[dict[str, Any]] | None, mcp_tools: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve the tool schemas and convert them to Anthropic format."""
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
    return _convert_tools_to_anthropic_format(tools_schemas)


def _resolve_max_output_tokens(provider: str, model: str | None = None) -> int:
    """Resolve max_tokens (config > model built-in default > 100k)."""
    max_output_tokens = load_max_output_tokens(provider, model)
    if max_output_tokens is None:
        max_output_tokens = get_default_max_output_tokens_from_provider(provider, model)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config
    return max_output_tokens


def _resolve_max_input_tokens(provider: str, model: str | None = None) -> int | None:
    """Resolve max input tokens (config override > model built-in default).

    Used for the usage summary display only; ``None`` means the context window
    is unknown, in which case the display omits the total.
    """
    max_input_tokens = load_max_input_tokens(provider, model)
    if max_input_tokens is None:
        max_input_tokens = get_default_max_input_tokens_from_provider(provider, model)
    return max_input_tokens


def _resolve_system_prompt(
    instructions: str | None, messages: list[dict[str, Any]]
) -> str | None:
    """Resolve the top-level ``system`` parameter from instructions/history."""
    system = instructions
    system_messages = [
        m for m in messages if m.get("role") == "system" and m.get("content")
    ]
    if system is None and system_messages:
        system = "\n\n".join(str(m.get("content")) for m in system_messages)
    return system


def _build_call_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    system: str | None,
) -> dict[str, Any]:
    """Build the Anthropic Messages call parameters for one round."""
    # System-role messages are filtered out of the payload; they were folded
    # into the top-level system parameter by _resolve_system_prompt.
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [m for m in messages if m.get("role") != "system"],
        "max_tokens": max_output_tokens,
    }
    if system:
        call_kwargs["system"] = system
    call_kwargs["stream"] = True
    return call_kwargs


def _handle_tool_blocks(
    tool_use_blocks: list[dict[str, Any]],
    full_content: str,
    messages: list[dict[str, Any]],
    tool_executor: ToolExecutor,
) -> None:
    """Record assistant tool_use blocks, execute them and append tool_results."""
    # Record the assistant's message with its content blocks (text +
    # tool_use) in the client-side history.
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

    # Execute every call and send the results back as tool_result blocks.
    tool_outputs: list[dict[str, Any]] = []
    for tc in tool_use_blocks:
        # Adapt the Anthropic tool-use shape to what the executor expects
        # (id + function{name, arguments}).
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


def _finalize_response(
    full_content: str,
    messages: list[dict[str, Any]],
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int,
    console: Console,
) -> str:
    """Record the final assistant message, print reports and return."""
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
        _display_usage(
            usage_info,
            max_input_tokens,
            max_output_tokens,
            len(messages),
            console,
            label="Messages",
            input_attr="input_tokens",
            output_attr="output_tokens",
            cached_details_attr=None,
        )
    return full_content


__all__ = [
    "send_prompt",
]
