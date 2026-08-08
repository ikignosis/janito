"""
Stream consumption for the native Anthropic Messages API.

These helpers are used by :mod:`janito.openai_client.anthropic_api`, which
talks to ``client.messages.create`` with streaming enabled.  The Messages API
streams typed events; blocks (text, thinking, tool_use) arrive as
``content_block_start`` / ``content_block_delta`` / ``content_block_stop``
triples, so each block is assembled per index and flushed when it stops, and
``message_stop`` is the terminal event.
"""

import json
import logging
from types import SimpleNamespace
from typing import Any

# Configure logger for this module
logger = logging.getLogger(__name__)


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
    state: dict[str, Any] = {
        "content": [],
        "reasoning": [],
        "tool_use_blocks": [],
        # index -> {type, text, id, name, json} while a block is in flight
        "blocks": {},
        "input_tokens": None,
        "output_tokens": None,
    }
    events_seen = 0

    for event in stream:
        events_seen += 1
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next event arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break
        if _handle_anthropic_event(event, state):
            break

    full_content = "".join(state["content"])
    reasoning_content = "".join(state["reasoning"]) if state["reasoning"] else None
    # A healthy stream always ends with message_stop; a stream with zero
    # events means the API failed before producing anything. Fail loudly
    # instead of returning an empty answer. An Enter-to-cancel short-circuit
    # must not be treated as an empty stream.
    if events_seen == 0 and (cancel_event is None or not cancel_event.is_set()):
        raise RuntimeError(
            "The Anthropic API returned no stream events (empty response)."
        )
    usage_info = None
    input_tokens = state["input_tokens"]
    output_tokens = state["output_tokens"]
    if input_tokens is not None or output_tokens is not None:
        usage_info = SimpleNamespace(
            total_tokens=(input_tokens or 0) + (output_tokens or 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return full_content, reasoning_content, state["tool_use_blocks"], usage_info


def _handle_anthropic_event(event, state: dict[str, Any]) -> bool:
    """Dispatch one stream event; return True when the stream is complete."""
    event_type = getattr(event, "type", None)
    if event_type == "message_start":
        _handle_message_start(event, state)
    elif event_type == "content_block_start":
        _handle_content_block_start(event, state)
    elif event_type == "content_block_delta":
        _handle_content_block_delta(event, state)
    elif event_type == "content_block_stop":
        _handle_content_block_stop(event, state)
    elif event_type == "message_delta":
        _handle_message_delta(event, state)
    elif event_type == "message_stop":
        # Terminal event: the response is fully consumed.
        return True
    elif event_type == "error":
        _raise_anthropic_error(event)
    return False


def _handle_message_start(event, state: dict[str, Any]) -> None:
    """Record the input tokens reported by the message_start event."""
    message = getattr(event, "message", None)
    if message is not None:
        usage = getattr(message, "usage", None)
        if usage is not None:
            state["input_tokens"] = getattr(usage, "input_tokens", None)


def _handle_content_block_start(event, state: dict[str, Any]) -> None:
    """Open a new content block indexed by ``index``."""
    index = getattr(event, "index", None)
    if index is None:
        return
    content_block = getattr(event, "content_block", None)
    state["blocks"][index] = {
        "type": getattr(content_block, "type", None),
        "text": "",
        "id": getattr(content_block, "id", None),
        "name": getattr(content_block, "name", None),
        "json": "",
    }


def _handle_content_block_delta(event, state: dict[str, Any]) -> None:
    """Accumulate text/thinking/JSON deltas into the in-flight block."""
    index = getattr(event, "index", None)
    block = state["blocks"].get(index)
    if block is None:
        return
    delta = getattr(event, "delta", None)
    if delta is None:
        return
    delta_type = getattr(delta, "type", None)
    if delta_type == "text_delta":
        block["text"] += getattr(delta, "text", "") or ""
    elif delta_type == "thinking_delta":
        block["text"] += getattr(delta, "thinking", "") or ""
    elif delta_type == "input_json_delta":
        block["json"] += getattr(delta, "partial_json", "") or ""


def _handle_content_block_stop(event, state: dict[str, Any]) -> None:
    """Flush a finished block into content, reasoning or tool_use_blocks."""
    index = getattr(event, "index", None)
    block = state["blocks"].pop(index, None)
    if block is None:
        return
    if block["type"] == "text":
        state["content"].append(block["text"])
    elif block["type"] == "thinking":
        if block["text"]:
            state["reasoning"].append(block["text"])
    elif block["type"] == "tool_use":
        state["tool_use_blocks"].append(_parse_tool_use_block(block))


def _parse_tool_use_block(block: dict[str, Any]) -> dict[str, Any]:
    """Parse a finished tool_use block into ``{"id", "name", "input"}``."""
    try:
        parsed = json.loads(block["json"]) if block["json"].strip() else {}
    except json.JSONDecodeError:
        logger.warning("Failed to parse Anthropic tool-use arguments")
        parsed = {}
    return {
        "id": block["id"],
        "name": block["name"],
        "input": parsed,
    }


def _handle_message_delta(event, state: dict[str, Any]) -> None:
    """Record the output tokens reported by the message_delta event."""
    usage = getattr(event, "usage", None)
    if usage is not None:
        state["output_tokens"] = getattr(usage, "output_tokens", None)


def _raise_anthropic_error(event) -> None:
    """Raise the error message carried by an error event."""
    error = getattr(event, "error", None)
    if isinstance(error, dict):
        message = error.get("message")
    else:
        message = getattr(error, "message", None)
    raise RuntimeError(message or "Anthropic API error")


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
