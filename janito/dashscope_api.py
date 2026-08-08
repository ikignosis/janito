"""
DashScope SDK client module for sending prompts through the **native**
DashScope SDK (``dashscope.Generation.call``).

This is the counterpart of :mod:`janito.openai_client.completions_api` for the
``"DashScope"`` API type: the same config resolution, tool loading, MCP
support, progress spinner, Enter-to-cancel, reasoning panel, used-files report
and token-usage summary, but talking to the DashScope native API through the
official ``dashscope`` package instead of an OpenAI-compatible endpoint.

The ``dashscope`` package is **optional**: the API type is only accepted by
``--set api-type=DashScope`` when the package is installed
(``provider_config.REQUIRES_BY_API_TYPE``), and this module refuses to run
without it, with an actionable install message.  Because the package may be
absent, the import happens lazily inside :func:`_create_client` (checked with
``importlib.util.find_spec``, mirroring the web-mode extra check) rather than
at module import time, so importing ``janito`` never requires ``dashscope``.

Like the Completions implementation, this module owns the conversation
history **client-side**: the DashScope generation API is stateless, so every
turn re-sends the full ``messages`` list.  Tool calls are executed with the
shared :class:`~janito.tooling.executor.ToolExecutor` and their ``tool``-role
messages are appended to the history before the next round, repeating until
the model emits a final text answer.  ``send_prompt`` returns the assistant
text and mutates ``previous_messages`` in place (Completions-style), so the
interactive shell treats this mode exactly like Completions.

Unlike the OpenAI-compatible types, the DashScope SDK talks to the **native**
DashScope API (``https://dashscope-intl.aliyuncs.com/api/v1`` for the
international region).  The base URL is a module-level global on the
``dashscope`` package (``dashscope.base_http_api_url``); it is set from the
provider's ``endpoint_by_api_type`` map (or a config endpoint override) before
each call.

The DashScope stream handling lives in
:mod:`janito.openai_client.dashscope_stream` and the shared client helpers in
:mod:`janito.openai_client.client_support`; both are re-exported here so
existing ``dashscope_api.<name>`` references keep working.
"""

from __future__ import annotations

import importlib.util
import logging
from types import SimpleNamespace
from typing import Any

from rich.console import Console

# Import general configuration handling
from janito.general_config import load_max_output_tokens

# Shared agent-loop pipeline (see Client.send) implemented by DashScopeClient.
from janito.openai_client.base_client import Client

# Shared client helpers (Rich console output, auth-error explainer) used by
# the module's remaining functions (finalize / error handling).
from janito.openai_client.client_support import _display_usage, _handle_auth_error

# Shared helpers reused from the Chat Completions implementation so all
# client modules stay in sync: runtime config resolution, the progress
# spinner / Enter-to-cancel runner and the request-cancelled signal.
from janito.openai_client.completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    resolve_runtime_config,
)
from janito.openai_client.dashscope_stream import (  # noqa: F401 (re-exported for backward compat)
    _build_tool_use_blocks,
    _build_usage_info,
    _consume_dashscope_chunk,
    _consume_message,
    _consume_stream,
    _consume_tool_call,
    _consume_usage,
    _get,
    _is_multimodal_model,
    _ModelEndpointMismatch,
    _raise_dashscope_error,
    _stream_response,
    _to_multimodal_messages,
)

# Import provider configuration for built-in defaults
from janito.provider_config import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_thinking_from_provider,
)

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.executor import ToolExecutor

# Import tools
from janito.tooling.tools_registry import get_all_tool_schemas

# Import used-files tracking (best-effort, never fails)
from janito.tooling.used_files import format_used_files

# Configure logger for this module
logger = logging.getLogger(__name__)


def _create_client(base_url: str | None, api_key: str) -> SimpleNamespace:
    """Prepare the native DashScope SDK client, guarding the optional package.

    The ``dashscope`` package is optional (see
    ``provider_config.REQUIRES_BY_API_TYPE``), so its availability is checked
    explicitly with ``importlib.util.find_spec`` (mirroring the web-mode extra
    check) and the import happens lazily -- importing ``janito`` never
    requires ``dashscope``.

    The DashScope SDK is stateless at the module level: the base URL is a
    module global (``dashscope.base_http_api_url``) and the API key is passed
    per call.  This helper therefore returns a lightweight handle carrying
    the resolved ``base_url`` / ``api_key`` for the call loop instead of a
    client object.

    Args:
        base_url: The native-SDK base URL (from the provider's
            ``endpoint_by_api_type`` map or a config endpoint override).
        api_key: The API key from the auth store.

    Returns:
        A ``SimpleNamespace`` with ``base_url`` and ``api_key``.

    Raises:
        RuntimeError: If the ``dashscope`` package is not installed, with an
            actionable install message.
    """
    if importlib.util.find_spec("dashscope") is None:
        raise RuntimeError(
            "API type 'DashScope' requires the optional 'dashscope' package, "
            "which is not installed. Install it with: pip install dashscope"
        )
    import dashscope

    # The DashScope SDK routes requests through the module-level
    # ``base_http_api_url`` global.  Point it at the resolved endpoint (the
    # provider's native-SDK base URL, or a config endpoint override) before
    # the first call; the API key is passed per call below.
    if base_url:
        dashscope.base_http_api_url = base_url
        logger.debug(f"DashScope base_http_api_url set to {base_url}")

    return SimpleNamespace(base_url=base_url, api_key=api_key)


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
    """Send a prompt through the native DashScope SDK and return the answer.

    Mirrors :func:`completions_api.send_prompt` (same config resolution, tool
    loading, spinner, reasoning panel, used-files report and usage summary)
    but targets the DashScope native generation API.  The conversation
    history is owned **client-side**: ``previous_messages`` is mutated in
    place (user and assistant turns are appended) so the interactive shell's
    history keeps growing, exactly like Completions mode.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation
            context (mutated in place).  DashScope accepts ``system``-role
            messages directly, so no extraction is needed (unlike the
            Anthropic Messages API).
        instructions: Accepted for signature parity with the other clients.
            DashScope takes the system prompt as a ``system``-role message in
            ``messages``; when provided as a string it is prepended as one.
        tools: Optional list of tool schemas to pass. If None, uses all
            available tools. If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: If True, enable thinking mode (``enable_thinking=True``).
            When False (default), falls back to the provider's built-in
            default, which is True for Alibaba/Qwen.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Accepted for signature parity with the other clients.
            The native DashScope SDK does not use ``reasoning_effort``
            (thinking depth is controlled by ``thinking_budget``, which is not
            wired yet).

    Returns:
        The assistant's final text (after any tool-call rounds).

    Raises:
        RuntimeError: If the ``dashscope`` package is not installed.
    """
    logger.info("Sending prompt to DashScope API (native SDK)")
    return DashScopeClient(
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


class DashScopeClient(Client):
    """Native DashScope SDK client (``Generation.call``).

    The conversation history is owned **client-side**: ``previous_messages``
    is mutated in place (user/assistant turns are appended), exactly like
    Completions mode.  The DashScope native API is stateless, so the full
    history is re-sent on every round.  Every hook forwards to this module's
    globals so test monkeypatches keep working.
    """

    api_type = "DashScope"
    backend_default = "https://dashscope-intl.aliyuncs.com/api/v1"

    def _resolve_runtime_config(self):
        # This module is the "DashScope" API type, so endpoint resolution
        # picks the native-SDK base URL from the endpoint_by_api_type map.
        return resolve_runtime_config(
            self.cli_model, self.cli_provider, cli_api_type="DashScope"
        )

    def _create_sdk_client(self, base_url, api_key):
        return _create_client(base_url, api_key)

    def _create_tool_executor(self, mcp_manager):
        return ToolExecutor(mcp_manager)

    def _resolve_tools(self, tools, mcp_tools):
        return _resolve_tools(tools, mcp_tools)

    def _resolve_model_settings(self, provider, thinking, reasoning_level):
        # The native DashScope SDK does not use reasoning_effort, so the
        # reasoning level is dropped (accepted for signature parity).
        thinking, max_output_tokens, max_input_tokens = _resolve_model_settings(
            provider, thinking
        )
        return thinking, max_output_tokens, max_input_tokens, None

    def _init_conversation_state(self, prompt, provider, **kwargs):
        # Build the conversation.  Unlike the Anthropic Messages API, DashScope
        # accepts ``system``-role messages directly, so the history is sent
        # as-is; a string ``instructions`` value is prepended as a system
        # message.
        return _init_messages(
            kwargs.get("instructions"), kwargs.get("previous_messages"), prompt
        )

    def _build_call_kwargs(
        self,
        model,
        state,
        max_output_tokens,
        reasoning_level,
        preserve_thinking,
        thinking,
    ):
        # The DashScope native API is stateless and the full history is
        # re-sent on every round.
        return _build_call_kwargs(model, state, max_output_tokens, thinking)

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
            # The dashscope SDK raises its own exception types; format the
            # common authentication failure with the same actionable details
            # as the OpenAI clients (the exception is always re-raised).
            _handle_auth_error(e, self.cli_provider, api_key, base_url, model, console)
            raise

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        # Record the assistant's message with its content and tool_calls in
        # the client-side history, then execute every call and send the
        # results back as tool-role messages before looping to get the final
        # answer.
        _handle_tool_blocks(
            tool_calls, full_content, reasoning_content, state, tool_executor
        )
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
            reasoning_content,
            state,
            usage_info,
            max_input_tokens,
            max_output_tokens,
            console,
        )


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
    provider: str, thinking: bool
) -> tuple[bool, int, int | None]:
    """Resolve thinking mode and token limits."""
    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # provider's built-in default applies (True for Alibaba/Qwen, which
    # reason by default). See provider_config.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider)

    # Max output tokens: the resolved value (config > provider built-in
    # default > 100k) is sent as the DashScope ``max_tokens`` parameter.
    max_output_tokens = load_max_output_tokens(provider)
    if max_output_tokens is None:
        max_output_tokens = get_default_max_output_tokens_from_provider(provider)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    # Load the provider's built-in max input tokens (context window) for the
    # usage summary display.
    max_input_tokens = get_default_max_input_tokens_from_provider(provider)
    return thinking, max_output_tokens, max_input_tokens


def _init_messages(
    instructions: str | None,
    previous_messages: list[dict[str, Any]] | None,
    prompt: str,
) -> list[dict[str, Any]]:
    """Build the conversation, prepending instructions as a system message."""
    messages = previous_messages if previous_messages is not None else []
    if instructions and not any(
        m.get("role") == "system" and m.get("content") for m in messages
    ):
        messages.insert(0, {"role": "system", "content": instructions})

    # NOTE: check `is not None` (not truthiness). An empty list is a valid,
    # caller-owned history (e.g. after a restart or with --no-system-prompt);
    # using a truthy check would replace it with a new local list and the
    # appended messages would never propagate back to the caller.
    messages.append({"role": "user", "content": prompt})
    return messages


def _build_call_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    thinking: bool,
) -> dict[str, Any]:
    """Build the DashScope call parameters for one round."""
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_output_tokens,
        "result_format": "message",
        "stream": True,
        "incremental_output": True,
    }
    # Enable thinking mode for Qwen models that support it (Alibaba/Qwen
    # reason by default).  Only set when True so models that always
    # reason keep their own default.
    if thinking:
        call_kwargs["enable_thinking"] = True
    return call_kwargs


def _handle_tool_blocks(
    tool_use_blocks: list[dict[str, str]],
    full_content: str,
    reasoning_content: str | None,
    messages: list[dict[str, Any]],
    tool_executor: ToolExecutor,
) -> None:
    """Record assistant tool_calls, execute them and append tool results."""
    # Record the assistant's message with its content and tool_calls in the
    # client-side history.
    assistant_tool_calls = []
    for tc in tool_use_blocks:
        assistant_tool_calls.append(
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
        )
    assistant_message = {
        "role": "assistant",
        "content": full_content,
        "tool_calls": assistant_tool_calls,
    }
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
    messages.append(assistant_message)

    # Execute every call and send the results back as tool-role messages.
    for tc in tool_use_blocks:
        # Adapt the DashScope tool-use shape to what the executor expects
        # (id + function{name, arguments}).
        adapted_call = {
            "id": tc["id"],
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            },
        }
        tool_message = tool_executor.execute_tool_call(adapted_call)
        messages.append(
            {
                "role": "tool",
                "content": tool_message["content"],
                "tool_call_id": tc["id"],
            }
        )


def _finalize_response(
    full_content: str,
    reasoning_content: str | None,
    messages: list[dict[str, Any]],
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int,
    console: Console,
) -> str:
    """Record the final assistant message, print reports and return."""
    # No more tool calls, return the final response. Record the final
    # assistant text in the client-side history.
    assistant_message = {"role": "assistant", "content": full_content}
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
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
            input_attr="input_tokens",
            output_attr="output_tokens",
            cached_details_attr=None,
        )
    return full_content


__all__ = [
    "RequestCancelled",
    "send_prompt",
]
