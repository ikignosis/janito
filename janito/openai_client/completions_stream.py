"""
Stream consumption for the Chat Completions API.

These helpers are shared by the OpenAI-compatible clients that talk to
``client.chat.completions.create`` with streaming enabled.  They assemble the
streamed deltas (content, reasoning/thinking text and tool-call arguments,
which arrive split across many chunks) into a single response and honour the
Enter-to-cancel ``cancel_event``.
"""

import logging

# Configure logger for this module
logger = logging.getLogger(__name__)


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming completion and assemble the response parts.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next chunk arrives.
    """
    collected_content: list[str] = []
    collected_reasoning: list[str] = []
    tool_calls_map: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}
    usage_info = None

    for chunk in stream:
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next chunk arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break

        # Usage stats arrive in the final chunk when include_usage is set
        if hasattr(chunk, "usage") and chunk.usage:
            usage_info = chunk.usage

        if not chunk.choices:
            continue

        _consume_chunk(
            chunk.choices[0].delta,
            collected_content,
            collected_reasoning,
            tool_calls_map,
        )

    full_content = "".join(collected_content)
    reasoning_content = "".join(collected_reasoning) if collected_reasoning else None
    return full_content, reasoning_content, tool_calls_map, usage_info


def _consume_chunk(
    delta,
    collected_content: list[str],
    collected_reasoning: list[str],
    tool_calls_map: dict[int, dict[str, str]],
) -> None:
    """Accumulate content, reasoning and tool-call deltas from one chunk."""
    # Collect reasoning / thinking content (DeepSeek R1, OpenAI o1/o3, ...)
    for attr in ("reasoning_content", "reasoning"):
        val = getattr(delta, attr, None)
        if val:
            collected_reasoning.append(val)
            break

    # Accumulate main content silently
    if delta.content:
        collected_content.append(delta.content)

    # Accumulate tool-call deltas (split across many chunks)
    if hasattr(delta, "tool_calls") and delta.tool_calls:
        for tc_delta in delta.tool_calls:
            _consume_tool_call_delta(tc_delta, tool_calls_map)


def _consume_tool_call_delta(
    tc_delta, tool_calls_map: dict[int, dict[str, str]]
) -> None:
    """Merge one tool-call delta into the per-index tool call map."""
    idx = tc_delta.index
    if idx not in tool_calls_map:
        tool_calls_map[idx] = {"id": "", "name": "", "arguments": ""}
    if tc_delta.id:
        tool_calls_map[idx]["id"] = tc_delta.id
    if tc_delta.function:
        if tc_delta.function.name:
            tool_calls_map[idx]["name"] = tc_delta.function.name
        if tc_delta.function.arguments:
            tool_calls_map[idx]["arguments"] += tc_delta.function.arguments


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming completion and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    if tools_schemas:
        logger.debug(f"Calling API (streaming) with {len(tools_schemas)} tools")
        stream = client.chat.completions.create(
            **call_kwargs,
            tools=tools_schemas,
            tool_choice="auto",
        )
    else:
        logger.debug("Calling API (streaming) without tools")
        stream = client.chat.completions.create(**call_kwargs)

    try:
        return _consume_stream(stream, cancel_event=cancel_event)
    finally:
        # Abort the underlying HTTP stream when the user pressed Enter so the
        # connection is released promptly instead of streaming to completion.
        if cancel_event is not None and cancel_event.is_set():
            stream.close()
