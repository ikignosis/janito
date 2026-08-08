"""
Stream consumption for the Responses API.

These helpers are used by :mod:`janito.openai_client.conversations_api`, which
talks to ``client.responses.create`` with streaming enabled.  The Responses
API emits typed SSE events (``response.output_text.delta``,
``response.function_call_arguments.delta``, ``response.output_item.done``,
...), so each finished output item carries a stable ``call_id`` (unlike Chat
Completions, which splits tool calls across chunks indexed by position).  The
helpers assemble the events into a single response and honour the
Enter-to-cancel ``cancel_event``.
"""

import logging
from typing import Any

# Configure logger for this module
logger = logging.getLogger(__name__)


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
    state: dict[str, Any] = {
        "content": [],
        "reasoning": [],
        "tool_calls": [],
        "partial_arguments": {},
        "usage_info": None,
        "response_id": None,
    }
    events_seen = 0

    for event in stream:
        events_seen += 1
        # Honour an Enter-to-cancel request: stop consuming as soon as the
        # next event arrives so the worker can close the connection.
        if cancel_event is not None and cancel_event.is_set():
            break
        _handle_stream_event(event, state)

    full_content = "".join(state["content"])
    reasoning_content = "".join(state["reasoning"]) if state["reasoning"] else None
    # A healthy stream always yields at least a response.created/completed
    # event; a stream with zero events means the provider failed to produce a
    # response (e.g. an error that was never surfaced). Fail loudly instead of
    # returning an empty answer. An Enter-to-cancel short-circuit must not be
    # treated as an empty stream.
    if events_seen == 0 and (cancel_event is None or not cancel_event.is_set()):
        raise RuntimeError(
            "The Responses API returned no stream events (empty response)."
        )
    return (
        full_content,
        reasoning_content,
        state["tool_calls"],
        state["usage_info"],
        state["response_id"],
    )


def _handle_stream_event(event, state: dict[str, Any]) -> None:
    """Dispatch a single stream event to the matching handler."""
    event_type = event.type

    # Some OpenAI-compatible providers stream API errors as SSE events the
    # SDK cannot type (``event.type`` is ``None``) but which carry the error
    # payload as ``code``/``message`` attributes. Alibaba DashScope, for
    # example, rejects a model its /responses endpoint does not support with
    # ``code='InvalidParameter'``, ``message="Unsupported model: 'qwen3.8-max'."``.
    # Surface the message instead of silently returning an empty response.
    if event_type is None:
        _handle_untyped_error(event)
        return

    if event_type in ("response.created", "response.completed"):
        _handle_completion_event(event, state)
    elif event_type == "response.failed":
        _raise_failed_error(event)
    elif event_type in (
        "response.output_text.delta",
        "response.reasoning_text.delta",
        "response.reasoning_summary_text.delta",
    ):
        _handle_text_delta(event, state)
    elif event_type in (
        "response.function_call_arguments.delta",
        "response.function_call_arguments.done",
    ):
        _handle_call_arguments(event, state)
    elif event_type == "response.output_item.done":
        _handle_output_item(event, state)


def _handle_untyped_error(event) -> None:
    """Raise for an untyped event carrying an error payload, else skip it."""
    message = getattr(event, "message", None)
    code = getattr(event, "code", None)
    if message or code:
        raise RuntimeError(f"{code}: {message}" if code else message)
    # Unknown untyped event with no error payload: skip it.


def _handle_completion_event(event, state: dict[str, Any]) -> None:
    """Record the response id (and usage on the completed event)."""
    # The response id is the handle used to chain the next turn; it is known
    # as soon as the server creates (or completes) the response.
    state["response_id"] = event.response.id
    if event.type == "response.completed" and event.response.usage:
        # Usage is delivered on the final event by default (it is part of the
        # Response object; "usage" is no longer a valid include value).
        state["usage_info"] = event.response.usage


def _raise_failed_error(event) -> None:
    """Raise the provider error carried by a response.failed event."""
    error = event.response.error
    message = error.message if error and error.message else "Response failed"
    raise RuntimeError(message)


def _handle_text_delta(event, state: dict[str, Any]) -> None:
    """Collect assistant text and reasoning deltas."""
    if not event.delta:
        return
    if event.type == "response.output_text.delta":
        state["content"].append(event.delta)
    else:
        state["reasoning"].append(event.delta)


def _handle_call_arguments(event, state: dict[str, Any]) -> None:
    """Assemble per-item function_call arguments (split across deltas)."""
    if event.type == "response.function_call_arguments.done":
        state["partial_arguments"][event.item_id] = event.arguments or ""
        return
    item_id = event.item_id
    state["partial_arguments"][item_id] = state["partial_arguments"].get(
        item_id, ""
    ) + (event.delta or "")


def _handle_output_item(event, state: dict[str, Any]) -> None:
    """Append a finished function_call output item to the tool calls."""
    item = event.item
    if getattr(item, "type", None) != "function_call":
        return
    state["tool_calls"].append(
        {
            "call_id": item.call_id,
            "name": item.name,
            "arguments": item.arguments or state["partial_arguments"].get(item.id, ""),
        }
    )


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
