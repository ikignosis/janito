"""
OpenAI client module for sending prompts to OpenAI-compatible endpoints using
the Responses API (``client.responses.create``) with server-side conversation
state.

This module mirrors :mod:`janito.openai_client.completions_api` (same config
resolution, tool loading, MCP support, progress spinner, reasoning panel,
used-files report and token-usage summary), but targets the Responses API
instead of the Chat Completions API.

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
(``responses_in_server`` is ``False`` in the provider's model config, e.g.
DeepSeek):
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

# Import the tool executor (routes tool calls to the MCP manager or the
# built-in registry and tracks usage/used-files/changes around each call)
from janito.tooling.executor import ToolExecutor

# Shared agent-loop pipeline (see Client.send) implemented by ResponsesClient.
from .base_client import Client

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
# modules stay in sync: runtime config resolution and the progress spinner
# runner.
from .completions_api import (
    RequestCancelled,
    _run_with_progress_bar,
    resolve_runtime_config,
)
from .responses_helpers import (
    _finalize_conversation,
    _handle_not_found_error,
    _handle_tool_calls,
    _pending_items_for_cancel,
    _resolve_model_settings,
    _resolve_tools,
    _validate_stream_result,
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

# Import general configuration handling

# Import provider configuration for built-in defaults


# Import tools

# Import used-files tracking (best-effort, never fails)


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
            for server-side providers, which chain with ``response_id``
            (``previous_items`` is then only used to carry the pending user
            messages of an Enter-cancelled turn).
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
        previous_items: For stateless providers (``responses_in_server``
            False), the full conversation as Responses input items (obtained
            from the previous result's ``input_items``), which cannot resolve
            a ``previous_response_id`` and must re-send the entire history on
            every request. For server-side providers it may carry the pending
            user messages of an Enter-cancelled turn, which are re-sent as
            input items chained from ``previous_response_id`` (the last
            completed response). ``None`` for a fresh conversation.
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
    return ResponsesClient(
        cli_model=cli_model,
        cli_provider=cli_provider,
        reasoning_level=reasoning_level,
        use_mcp=use_mcp,
    ).send(
        prompt,
        verbose=verbose,
        previous_response_id=previous_response_id,
        previous_items=previous_items,
        instructions=instructions,
        tools=tools,
        thinking=thinking,
    )


class ResponsesClient(Client):
    """Responses API client (``client.responses.create``).

    The conversation state model depends on the provider: server-side
    endpoints (e.g. OpenAI) chain turns with ``previous_response_id`` (the
    history lives on the server); stateless endpoints (e.g. DeepSeek) track
    the full conversation as Responses input items and re-send them on every
    request.  Every hook forwards to this module's globals so test
    monkeypatches keep working.
    """

    api_type = "Responses"

    def _resolve_runtime_config(self):
        return resolve_runtime_config(self.cli_model, self.cli_provider)

    def _create_sdk_client(self, base_url, api_key):
        # base_url can be None for standard OpenAI
        return OpenAI(api_key=api_key, base_url=base_url)

    def _create_tool_executor(self, mcp_manager):
        return ToolExecutor(mcp_manager)

    def _resolve_tools(self, tools, mcp_tools):
        return _resolve_tools(tools, mcp_tools)

    def _resolve_model_settings(self, provider, model, thinking, reasoning_level):
        return _resolve_model_settings(provider, model, thinking, reasoning_level)

    def _init_conversation_state(self, prompt, provider, model, **kwargs):
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
            pending_items,
        ) = _init_conversation_state(
            provider,
            model,
            kwargs.get("previous_response_id"),
            kwargs.get("previous_items"),
            kwargs.get("instructions"),
            prompt,
        )
        return {
            "responses_in_server": responses_in_server,
            "response_id": response_id,
            "conversation_items": conversation_items,
            "input_items": input_items,
            "pending_items": pending_items,
            "instructions": kwargs.get("instructions"),
            "message_count": 1,
        }

    def _build_call_kwargs(
        self,
        model,
        state,
        max_output_tokens,
        reasoning_level,
        preserve_thinking,
        thinking,
    ):
        return _build_call_kwargs(
            model,
            state["input_items"],
            max_output_tokens,
            reasoning_level,
            preserve_thinking,
            thinking,
            state["response_id"],
            state["responses_in_server"],
            state["instructions"],
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
            if state["responses_in_server"]:
                state["response_id"] = stream_response_id
            # Safety net: a server-side provider that never reported a
            # response id and produced neither content nor tool calls means
            # the request failed without a proper error event. Raise a clear
            # error naming the model instead of returning an empty result.
            _validate_stream_result(
                state["responses_in_server"],
                stream_response_id,
                full_content,
                tool_calls,
                model,
            )
        except NotFoundError as e:
            _handle_not_found_error(e, base_url, model, state["response_id"], console)
            raise
        except AuthenticationError as e:
            _handle_auth_error(e, self.cli_provider, api_key, base_url, model, console)
            raise
        except RequestCancelled as e:
            # Enter was pressed while waiting for the API. Keep the
            # conversation state so the shell can continue without losing the
            # user's message:
            #  - server-side: the aborted request created a server-side
            #    response carrying the message, but the provider discards it
            #    when the stream is interrupted (OpenAI answers
            #    ``previous_response_id not found`` for it), so it cannot
            #    chain the next turn. The caller keeps the last *completed*
            #    response id (state["response_id"]) and re-sends the pending
            #    user messages as input items chained from it.
            #  - stateless: the server keeps nothing, so hand back the full
            #    client-side items (which already include the cancelled
            #    message) for the next turn to re-send.
            if state["responses_in_server"]:
                e.conversation_items = _pending_items_for_cancel(state)
            else:
                e.conversation_items = state["input_items"]
            raise
        return full_content, reasoning_content, tool_calls, usage_info

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        # Record the assistant's tool calls in the client-side history
        # (stateless providers) and execute every call, sending the results
        # back as function_call_output items chained to the response that
        # produced the calls (server-side) or appended to the full history
        # (stateless). Then continue the loop.
        state["input_items"] = _handle_tool_calls(
            tool_calls, full_content, state["conversation_items"], tool_executor
        )
        state["message_count"] += 1
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
        # Server-side: the assistant message lives on the server and the
        # caller only needs the response id to chain the next turn. Stateless:
        # append the final assistant text to the client-side history and hand
        # the full items back so the caller can re-send them next turn.
        return _finalize_conversation(
            full_content,
            state["conversation_items"],
            usage_info,
            max_input_tokens,
            max_output_tokens,
            state["message_count"],
            console,
            state["response_id"],
            state["responses_in_server"],
        )


__all__ = [
    "ConversationResult",
    "get_env_config",
    "resolve_runtime_config",
    "send_prompt",
]
