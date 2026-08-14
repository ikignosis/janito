"""
Shared module-level helpers for the DashScope client.

Extracted from :mod:`janito.dashscope_api` so the client module stays focused
on the ``send_prompt`` entry point and the :class:`DashScopeClient` class.
"""

import logging
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
    provider: str, model: str, thinking: bool
) -> tuple[bool, int, int | None]:
    """Resolve thinking mode and token limits for ``model``."""
    # Thinking mode: the explicit --thinking flag wins, otherwise the
    # model's built-in default applies (True for Alibaba/Qwen, which
    # reason by default). See provider_config.PROVIDER_INFO.
    if not thinking:
        thinking = get_default_thinking_from_provider(provider, model)

    # Max output tokens: the resolved value (config > model built-in
    # default > 100k) is sent as the DashScope ``max_tokens`` parameter.
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
