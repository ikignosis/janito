"""
Gemini SDK client module for sending prompts through the **native** Gemini
API (``client.models.generate_content_stream``, the stable ``generateContent``
API from the ``google-genai`` package).

This is the counterpart of :mod:`janito.openai_client.completions_api` for the
``"Gemini"`` API type: the same config resolution, tool loading, MCP support,
progress spinner, reasoning panel, used-files report and token-usage summary,
but talking to the native Gemini API through the official ``google-genai``
package instead of Google's OpenAI-compatibility layer.

The ``google-genai`` package is **optional**: the API type is only accepted by
``--set api-type=Gemini`` when the package is installed
(``janito.providers.REQUIRES_BY_API_TYPE``), and this module refuses to run
without it, with an actionable install message.  Because the package may be
absent, the import happens lazily inside :func:`_create_client` (checked with
``importlib.util.find_spec``, mirroring the web-mode extra check) rather than
at module import time, so importing ``janito`` never requires ``google-genai``.

Like the Completions implementation, this module owns the conversation history
**client-side**: the Gemini ``generateContent`` API is stateless, so every
turn re-sends the full ``contents`` list (plus the top-level
``system_instruction``).  Tool calls are executed with the shared
:class:`~janito.tooling.executor.ToolExecutor` and their ``function_response``
parts are appended to the history before the next round, repeating until the
model emits a final text answer.  ``send_prompt`` returns the assistant text
and mutates ``previous_messages`` in place (Completions-style), so the
interactive shell treats this mode exactly like Completions.

Gemini 3.x models reason by default: thought parts stream alongside the
answer and are surfaced in the reasoning panel.  Stateless multi-turn
requests must resend the model's thought blocks verbatim, so the client keeps
them (``thought_parts`` plus the per-call ``thought_signature``) in the
client-side history and echoes them back on the next round.

The Gemini stream handling lives in :mod:`janito.openai_client.gemini_stream`
and the wire-format helpers in :mod:`janito.gemini_helpers`; both are
re-exported here so existing ``gemini_api.<name>`` references keep working.
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any

from janito.gemini_helpers import (  # noqa: F401 (re-exported for backward compat)
    _build_call_kwargs,
    _finalize_response,
    _handle_tool_parts,
    _init_state,
    _messages_to_contents,
    _resolve_model_settings,
    _resolve_system_instruction,
    _resolve_tools,
)

# Shared agent-loop pipeline (see Client.send) implemented by GeminiClient.
from janito.openai_client.base_client import Client

# Shared client helpers (Rich console output, auth-error explainer) used by
# the module's remaining functions (finalize / error handling).
from janito.openai_client.client_support import _handle_auth_error

# Shared helpers reused from the Chat Completions implementation so all
# client modules stay in sync: runtime config resolution and the progress
# spinner runner.
from janito.openai_client.completions_api import (
    _run_with_progress_bar,
    resolve_runtime_config,
)
from janito.openai_client.gemini_stream import (  # noqa: F401 (re-exported for backward compat)
    _consume_chunk,
    _consume_stream,
    _stream_response,
)
from janito.tooling.executor import ToolExecutor

# Configure logger for this module
logger = logging.getLogger(__name__)


def _create_client(base_url: str | None, api_key: str) -> Any:
    """Create the native Gemini SDK client, guarding the optional package.

    The ``google-genai`` package is optional (see
    ``janito.providers.REQUIRES_BY_API_TYPE``), so its availability is checked
    explicitly with ``importlib.util.find_spec`` (mirroring the web-mode extra
    check) and the import happens lazily -- importing ``janito`` never
    requires ``google-genai``.

    Args:
        base_url: The native-SDK base URL (from the provider's
            ``endpoint_by_api_type`` map or a config endpoint override).
            ``None`` uses the SDK's default
            (``https://generativelanguage.googleapis.com``).
        api_key: The API key from the auth store.

    Returns:
        A ``google.genai.Client`` instance.

    Raises:
        RuntimeError: If the ``google-genai`` package is not installed, with
            an actionable install message.
    """
    try:
        spec = importlib.util.find_spec("google.genai")
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise RuntimeError(
            "API type 'Gemini' requires the optional 'google-genai' package, "
            "which is not installed. Install it with: pip install google-genai"
        )
    from google import genai

    http_options = {"base_url": base_url} if base_url else None
    return genai.Client(api_key=api_key, http_options=http_options)


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
    """Send a prompt through the native Gemini SDK and return the answer.

    Mirrors :func:`completions_api.send_prompt` (same config resolution, tool
    loading, spinner, reasoning panel, used-files report and usage summary)
    but targets the native Gemini ``generateContent`` API.  The conversation
    history is owned **client-side**: ``previous_messages`` is mutated in
    place (user and assistant turns are appended) so the interactive shell's
    history keeps growing, exactly like Completions mode.

    Args:
        prompt: The user prompt to send
        verbose: If True, print model and backend info
        previous_messages: List of previous message dicts for conversation
            context (mutated in place). A leading ``"system"``-role message is
            extracted and sent as the top-level Gemini
            ``system_instruction``.
        instructions: System instructions for the conversation (sent as the
            top-level Gemini ``system_instruction``). When ``None``, a
            leading ``"system"``-role message in ``previous_messages`` is
            used.
        tools: Optional list of tool schemas to pass. If None, uses all
            available tools. If an empty list, no tools are passed.
        use_mcp: If True, load and use MCP tools (default True)
        thinking: Accepted for signature parity with the other clients.
            Gemini 3.x models reason by default; thinking depth is controlled
            through ``reasoning_level`` (mapped to the model's
            ``thinking_level``) instead of a thinking flag.
        cli_model: Model passed via ``--model`` (overrides the provider's config).
        cli_provider: Provider passed via ``--provider`` (overrides config/auth).
        reasoning_level: Reasoning depth passed via ``--reasoning-level``.
            Sent to the native API as ``thinking_config.thinking_level``,
            which the Gemini API maps to the model's thinking depth.

    Returns:
        The assistant's final text (after any tool-call rounds).

    Raises:
        RuntimeError: If the ``google-genai`` package is not installed.
    """
    logger.info("Sending prompt to Gemini API (native SDK)")
    return GeminiClient(
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


class GeminiClient(Client):
    """Native Gemini SDK client (``client.models.generate_content_stream``).

    The conversation history is owned **client-side**: ``previous_messages``
    is mutated in place (user/assistant turns are appended), exactly like
    Completions mode.  The Gemini ``generateContent`` API is stateless, so the
    full history is re-sent (converted to Gemini ``contents``) on every
    round.  Every hook forwards to this module's globals so test
    monkeypatches keep working.
    """

    api_type = "Gemini"
    backend_default = "https://generativelanguage.googleapis.com"

    def _resolve_runtime_config(self):
        # This module is the "Gemini" API type, so endpoint resolution picks
        # the native-SDK base URL from the endpoint_by_api_type map.
        return resolve_runtime_config(
            self.cli_model, self.cli_provider, cli_api_type="Gemini"
        )

    def _create_sdk_client(self, base_url, api_key):
        return _create_client(base_url, api_key)

    def _create_tool_executor(self, mcp_manager):
        return ToolExecutor(mcp_manager)

    def _resolve_tools(self, tools, mcp_tools):
        return _resolve_tools(tools, mcp_tools)

    def _resolve_model_settings(self, provider, model, thinking, reasoning_level):
        return _resolve_model_settings(provider, model, thinking, reasoning_level)

    def _init_conversation_state(self, prompt, provider, model, **kwargs):
        # Build the conversation. The Gemini API takes the system prompt as a
        # top-level `system_instruction` (not a "system"-role content), so
        # system-role messages are extracted from the history and folded into
        # it; the in-place history list keeps them so the shell's
        # messages_history stays intact.
        return _init_state(
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
        # The effective model's built-in (native) tools would be resolved for
        # the Gemini API type here (get_default_tools_from_provider with
        # api_type="Gemini"); the google provider declares none, so no
        # built-in tools are sent.  Function tools are converted to Gemini
        # function_declarations inside gemini_helpers._build_call_kwargs.
        from janito.provider_accessors import get_default_tools_from_provider

        tools = get_default_tools_from_provider(
            self._active_provider(), model, api_type="Gemini"
        )
        return _build_call_kwargs(
            model,
            state["messages"],
            max_output_tokens,
            state["system"],
            reasoning_level,
            tools,
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
                raw_attrs,
                thought_parts,
            ) = _run_with_progress_bar(
                _stream_response, client, call_kwargs, tools_schemas
            )
        except Exception as e:
            # The google-genai SDK raises its own exception types (APIError);
            # format the common authentication failure (HTTP 401) with the
            # same actionable details as the OpenAI clients by adapting the
            # status code the shared explainer reads (the exception is always
            # re-raised).
            if getattr(e, "code", None) == 401:
                e.status_code = 401
            _handle_auth_error(e, self.cli_provider, api_key, base_url, model, console)
            raise
        # The model's thought blocks (text + signature) must be resent
        # verbatim on the next round; carry them through the conversation
        # state for the tool-call / finalize hooks.
        state["thought_parts"] = thought_parts
        return full_content, reasoning_content, tool_calls, usage_info, raw_attrs

    def _handle_tool_calls(
        self, tool_calls, full_content, reasoning_content, state, tool_executor
    ):
        # Record the assistant's message with its content blocks (text +
        # function_call parts) in the client-side history, then execute every
        # call and send the results back as function_response parts before
        # looping to get the final answer.
        _handle_tool_parts(
            tool_calls,
            full_content,
            reasoning_content,
            state.get("thought_parts") or [],
            state["messages"],
            tool_executor,
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
        provider=None,
        model=None,
    ):
        # No more tool calls, return the final response.
        return _finalize_response(
            full_content,
            reasoning_content,
            state.get("thought_parts") or [],
            state["messages"],
            usage_info,
            max_input_tokens,
            max_output_tokens,
            console,
            provider=provider,
            model=model,
        )


__all__ = [
    "send_prompt",
]
