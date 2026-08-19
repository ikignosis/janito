"""
Shared module-level helpers for the native Gemini client.

Extracted from :mod:`janito.gemini_api` so the client module stays focused
on the ``send_prompt`` entry point and the :class:`GeminiClient` class.  The
wire-format conversions (OpenAI-format chat ``messages`` -> Gemini
``contents``, tool schemas -> ``function_declarations``, usage metadata ->
the shared token-usage shape) live here so the web agent's shared adapter
(:mod:`janito.agent.gemini`) reuses them instead of duplicating them.
"""

import json
import logging
from types import SimpleNamespace
from typing import Any

from rich.console import Console

from janito.config_loaders import load_max_input_tokens, load_max_output_tokens
from janito.openai_client.client_support import _display_usage
from janito.provider_accessors import (
    get_default_max_input_tokens_from_provider,
    get_default_max_output_tokens_from_provider,
    get_default_thinking_from_provider,
)
from janito.tooling.executor import ToolExecutor
from janito.tooling.tools_registry import get_all_tool_schemas
from janito.tooling.used_files import format_used_files

# Configure logger for this module
logger = logging.getLogger(__name__)


def _resolve_tools(
    tools: list[dict[str, Any]] | None, mcp_tools: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve the tool schemas (built-in + MCP) in OpenAI format."""
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


def _convert_tools_to_gemini_format(
    tools_schemas: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Convert OpenAI-format tool schemas to Gemini ``function_declarations``.

    The shared schema builders emit the Chat Completions shape (``type``
    ``"function"`` with the declaration nested under ``"function"``).  The
    Gemini API expects ``tools=[{"function_declarations": [{name,
    description, parameters}]}]``; ``parameters`` is passed through as-is
    (the Gemini API accepts the OpenAPI subset natively).

    Returns ``None`` when there are no tools (the caller then omits the
    ``tools`` key from the request).
    """
    if not tools_schemas:
        return None
    declarations = []
    for schema in tools_schemas:
        function = schema.get("function") if isinstance(schema, dict) else None
        if function is None:
            continue
        declaration: dict[str, Any] = {}
        if function.get("name"):
            declaration["name"] = function["name"]
        if function.get("description"):
            declaration["description"] = function["description"]
        parameters = function.get("parameters")
        if parameters:
            declaration["parameters"] = parameters
        if declaration:
            declarations.append(declaration)
    if not declarations:
        return None
    return [{"function_declarations": declarations}]


def _resolve_system_instruction(
    instructions: str | None, messages: list[dict[str, Any]]
) -> str | None:
    """Resolve the Gemini ``system_instruction`` from instructions/history."""
    system = instructions
    system_messages = [
        m for m in messages if m.get("role") == "system" and m.get("content")
    ]
    if system is None and system_messages:
        system = "\n\n".join(str(m.get("content")) for m in system_messages)
    return system


def _assistant_parts(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the Gemini ``model`` parts for an assistant message.

    The model's thought blocks (text + signature) are resent verbatim, then
    the final text and any ``function_call`` parts (each carrying the model's
    ``thought_signature`` when one was attached).
    """
    parts: list[dict[str, Any]] = []
    for thought in msg.get("thought_parts") or []:
        thought_part: dict[str, Any] = {"text": thought.get("text") or ""}
        if thought.get("thought_signature"):
            thought_part["thought_signature"] = thought["thought_signature"]
        parts.append(thought_part)
    content = msg.get("content")
    if content:
        parts.append({"text": content})
    for tc in msg.get("tool_calls") or []:
        function = tc.get("function") or {}
        call_part: dict[str, Any] = {
            "function_call": {
                "id": tc.get("id") or "",
                "name": function.get("name") or "",
                "args": _parse_arguments(function.get("arguments")),
            }
        }
        if tc.get("thought_signature"):
            call_part["thought_signature"] = tc["thought_signature"]
        parts.append(call_part)
    return parts


def _tool_result_part(msg: dict[str, Any]) -> dict[str, Any]:
    """Build the Gemini ``user`` part carrying a ``function_response``.

    The Gemini ``function_response.response`` field must be a JSON object
    (``dict``): the ``google-genai`` SDK rejects plain-text tool results
    (markdown, logs, ...) and non-object JSON values (lists, scalars) with a
    client-side pydantic error, so they are wrapped under a ``result`` key
    (the documented convention for free-form tool output).
    """
    response = msg.get("content")
    try:
        response = json.loads(response) if isinstance(response, str) else response
    except (ValueError, TypeError):
        pass
    if response is not None and not isinstance(response, dict):
        response = {"result": response}
    response_part: dict[str, Any] = {
        "function_response": {
            "id": msg.get("tool_call_id") or "",
            "name": msg.get("name") or "",
            "response": response,
        }
    }
    if msg.get("thought_signature"):
        response_part["thought_signature"] = msg["thought_signature"]
    return response_part


def _messages_to_contents(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert OpenAI-format chat messages to Gemini ``contents`` (dict shape).

    The Gemini API takes ``contents`` as a list of ``{"role": "user" |
    "model", "parts": [...]}`` parts.  ``system``-role messages are skipped
    (they were folded into the top-level ``system_instruction`` by
    :func:`_resolve_system_instruction`); ``tool``-role messages become
    ``user`` parts carrying a ``function_response``.

    Gemini 3.x attaches thought signatures to parts; stateless multi-turn
    requests must resend the model's thought blocks verbatim (see the
    generateContent thinking guide).  The assistant messages recorded by
    this client keep the raw thought parts (``thought_parts``) and per-call
    signatures (``tool_calls[*].thought_signature``), which are re-attached
    here so reasoning continuity is preserved across turns.
    """
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue
        if role == "assistant":
            parts = _assistant_parts(msg)
            if parts:
                contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            # Tool results go back as user parts with a function_response.
            contents.append({"role": "user", "parts": [_tool_result_part(msg)]})
        else:
            # Plain user turn.  A leading system-role message was already
            # folded into system_instruction, so this is the user's text.
            content = msg.get("content")
            contents.append({"role": "user", "parts": [{"text": str(content)}]})
    return contents


def _parse_arguments(arguments: Any) -> dict[str, Any]:
    """Parse a tool-call arguments JSON string into a dict (best effort)."""
    if isinstance(arguments, dict):
        return arguments
    try:
        parsed = json.loads(arguments) if arguments else {}
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _build_usage_info(usage_metadata: Any) -> SimpleNamespace | None:
    """Map Gemini ``usage_metadata`` onto the shared token-usage shape.

    The shared usage display / normalization reads ``total_tokens`` /
    ``input_tokens`` / ``output_tokens`` attributes; Gemini reports
    ``total_token_count`` / ``prompt_token_count`` / ``response_token_count``
    (plus ``thoughts_token_count``), so they are mapped onto a
    ``SimpleNamespace`` exactly like the Anthropic / DashScope native
    clients do.
    """
    if usage_metadata is None:
        return None
    return SimpleNamespace(
        total_tokens=getattr(usage_metadata, "total_token_count", None),
        input_tokens=getattr(usage_metadata, "prompt_token_count", None),
        output_tokens=getattr(usage_metadata, "response_token_count", None),
    )


def _resolve_model_settings(
    provider: str, model: str, thinking: bool, reasoning_level: str | None
) -> tuple[bool, int, int | None, str | None]:
    """Resolve thinking mode, token limits and reasoning level for ``model``."""
    # Thinking mode: the explicit --thinking flag wins, otherwise the model's
    # built-in default applies.  Gemini 3.x models reason by default, but the
    # thinking flag itself is not sent on the native API (thinking depth is
    # controlled through reasoning_level -> thinking_level instead).
    if not thinking:
        thinking = get_default_thinking_from_provider(provider, model)

    # Max output tokens: the resolved value (config > model built-in default
    # > 100k) is sent as the Gemini ``max_output_tokens`` config field.
    max_output_tokens = load_max_output_tokens(provider, model)
    if max_output_tokens is None:
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
    return thinking, max_output_tokens, max_input_tokens, reasoning_level


def _init_state(
    instructions: str | None,
    previous_messages: list[dict[str, Any]] | None,
    prompt: str,
) -> dict[str, Any]:
    """Build the per-turn conversation state (messages + system instruction)."""
    messages = previous_messages if previous_messages is not None else []
    system = _resolve_system_instruction(instructions, messages)

    # NOTE: check `is not None` (not truthiness). An empty list is a valid,
    # caller-owned history (e.g. after a restart or with --no-system-prompt);
    # using a truthy check would replace it with a new local list and the
    # appended messages would never propagate back to the caller.
    messages.append({"role": "user", "content": prompt})
    return {"messages": messages, "system": system}


def _build_call_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    system: str | None,
    reasoning_level: str | None,
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build the native Gemini ``generate_content`` call parameters.

    The OpenAI-format history is converted to Gemini ``contents`` and the
    tool schemas to ``function_declarations``; ``max_output_tokens`` and the
    resolved reasoning level (sent as ``thinking_config.thinking_level``,
    which the Gemini API maps to the model's thinking depth) ride in the
    ``config`` dict.  ``tools`` is the effective model's built-in (native)
    tools list from the provider config; built-in tools are not function
    tools, so they are not sent here (the native Gemini API enables Google
    Search / code execution through their own ``Tool`` entries, which are
    not wired for this API type yet).
    """
    config: dict[str, Any] = {"max_output_tokens": max_output_tokens}
    if system:
        config["system_instruction"] = system
    if reasoning_level:
        config["thinking_config"] = {"thinking_level": reasoning_level}
    function_tools = _convert_tools_to_gemini_format(tools)
    if function_tools:
        config["tools"] = function_tools
    return {
        "model": model,
        "contents": _messages_to_contents(messages),
        "config": config,
    }


def _handle_tool_parts(
    tool_calls: list[dict[str, Any]],
    full_content: str,
    reasoning_content: str | None,
    thought_parts: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    tool_executor: ToolExecutor,
) -> None:
    """Record assistant tool_calls, execute them and append tool results.

    The assistant message keeps the model's thought blocks (``thought_parts``)
    and per-call ``thought_signature`` values so the next round can resend
    them verbatim (Gemini 3.x rejects follow-up requests that drop them with
    a 400 "Function call is missing a thought_signature" error).  Tool
    results are appended as ``tool``-role messages carrying the call id,
    name and thought signature.
    """
    assistant_tool_calls = []
    for tc in tool_calls:
        call = {
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            },
        }
        if tc.get("thought_signature"):
            call["thought_signature"] = tc["thought_signature"]
        assistant_tool_calls.append(call)
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": full_content,
        "tool_calls": assistant_tool_calls,
    }
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
    if thought_parts:
        assistant_message["thought_parts"] = thought_parts
    messages.append(assistant_message)

    # Execute every call and send the results back as tool-role messages.
    for tc in tool_calls:
        adapted_call = {
            "id": tc["id"],
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            },
        }
        tool_message = tool_executor.execute_tool_call(adapted_call)
        result: dict[str, Any] = {
            "role": "tool",
            "content": tool_message["content"],
            "tool_call_id": tc["id"],
            "name": tc["name"],
        }
        if tc.get("thought_signature"):
            result["thought_signature"] = tc["thought_signature"]
        messages.append(result)


def _finalize_response(
    full_content: str,
    reasoning_content: str | None,
    thought_parts: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    usage_info: Any,
    max_input_tokens: int | None,
    max_output_tokens: int,
    console: Console,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Record the final assistant message, print reports and return."""
    # No more tool calls, return the final response. Record the final
    # assistant text in the client-side history (keeping the model's thought
    # blocks so follow-up turns can resend them verbatim).
    assistant_message: dict[str, Any] = {"role": "assistant", "content": full_content}
    if reasoning_content:
        assistant_message["reasoning_content"] = reasoning_content
    if thought_parts:
        assistant_message["thought_parts"] = thought_parts
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
            provider=provider,
            model=model,
        )
    return full_content
