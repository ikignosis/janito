"""
Stream consumption for the Responses API.

These helpers are used by :mod:`janito.openai_client.conversations_api`, which
talks to ``client.responses.create`` with streaming enabled.  The Responses
API emits typed SSE events (``response.output_text.delta``,
``response.function_call_arguments.delta``, ``response.output_item.done``,
...), so each finished output item carries a stable ``call_id`` (unlike Chat
Completions, which splits tool calls across chunks indexed by position).

:class:`ResponsesStreamConsumer` is the real implementation: it holds the
assembled response parts as instance attributes (no ``state`` dict plumbing)
and drives the per-event handlers.  The module-level ``_consume_response_stream``
/ ``_handle_*`` functions are thin delegators kept for backward compatibility
(they are re-exported from ``conversations_api``).
"""

import logging
from typing import Any

# Configure logger for this module
logger = logging.getLogger(__name__)


class ResponsesStreamConsumer:
    """Assemble Responses API stream events into a single response.

    The consumer owns the accumulated content / reasoning text, the tool-call
    list (with stable ``call_id`` per finished output item), the per-item
    partial-arguments buffer, the usage info and the server-side response id.
    :meth:`consume` drives the stream and returns the response parts; the
    ``handle_*`` methods apply individual events.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.partial_arguments: dict[str, str] = {}
        self.usage_info: Any = None
        self.response_id: str | None = None
        self._events_seen = 0

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def full_content(self) -> str:
        """The assembled assistant text."""
        return "".join(self.content)

    @property
    def reasoning_content(self) -> str | None:
        """The assembled reasoning text, or ``None`` when none was streamed."""
        return "".join(self.reasoning) if self.reasoning else None

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def consume(self, stream, cancel_event=None):
        """Consume a streaming Responses API response and assemble its parts.

        Returns ``(full_content, reasoning_content, tool_calls, usage_info,
        response_id)`` where ``tool_calls`` is a list of
        ``{"call_id", "name", "arguments"}`` dicts.

        When ``cancel_event`` is set (user pressed Enter while waiting), the
        stream is abandoned as soon as the next event arrives.
        """
        for event in stream:
            self._events_seen += 1
            # Honour an Enter-to-cancel request: stop consuming as soon as the
            # next event arrives so the worker can close the connection.
            if cancel_event is not None and cancel_event.is_set():
                break
            self.handle_event(event)

        # A healthy stream always yields at least a response.created/completed
        # event; a stream with zero events means the provider failed to
        # produce a response (e.g. an error that was never surfaced). Fail
        # loudly instead of returning an empty answer. An Enter-to-cancel
        # short-circuit must not be treated as an empty stream.
        if self._events_seen == 0 and (
            cancel_event is None or not cancel_event.is_set()
        ):
            raise RuntimeError(
                "The Responses API returned no stream events (empty response)."
            )
        return (
            self.full_content,
            self.reasoning_content,
            self.tool_calls,
            self.usage_info,
            self.response_id,
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_event(self, event) -> None:
        """Dispatch a single stream event to the matching handler."""
        event_type = event.type

        # Some OpenAI-compatible providers stream API errors as SSE events the
        # SDK cannot type (``event.type`` is ``None``) but which carry the
        # error payload as ``code``/``message`` attributes. Alibaba DashScope,
        # for example, rejects a model its /responses endpoint does not
        # support with ``code='InvalidParameter'``, ``message="Unsupported
        # model: 'qwen3.8-max'."``.  Surface the message instead of silently
        # returning an empty response.
        if event_type is None:
            _handle_untyped_error(event)
            return

        if event_type in ("response.created", "response.completed"):
            self.handle_completion_event(event)
        elif event_type == "response.failed":
            _raise_failed_error(event)
        elif event_type in (
            "response.output_text.delta",
            "response.reasoning_text.delta",
            "response.reasoning_summary_text.delta",
        ):
            self.handle_text_delta(event)
        elif event_type in (
            "response.function_call_arguments.delta",
            "response.function_call_arguments.done",
        ):
            self.handle_call_arguments(event)
        elif event_type == "response.output_item.done":
            self.handle_output_item(event)

    def handle_completion_event(self, event) -> None:
        """Record the response id (and usage on the completed event)."""
        # The response id is the handle used to chain the next turn; it is
        # known as soon as the server creates (or completes) the response.
        self.response_id = event.response.id
        if event.type == "response.completed" and event.response.usage:
            # Usage is delivered on the final event by default (it is part of
            # the Response object; "usage" is no longer a valid include value).
            self.usage_info = event.response.usage

    def handle_text_delta(self, event) -> None:
        """Collect assistant text and reasoning deltas."""
        if not event.delta:
            return
        if event.type == "response.output_text.delta":
            self.content.append(event.delta)
        else:
            self.reasoning.append(event.delta)

    def handle_call_arguments(self, event) -> None:
        """Assemble per-item function_call arguments (split across deltas)."""
        if event.type == "response.function_call_arguments.done":
            self.partial_arguments[event.item_id] = event.arguments or ""
            return
        item_id = event.item_id
        self.partial_arguments[item_id] = self.partial_arguments.get(item_id, "") + (
            event.delta or ""
        )

    def handle_output_item(self, event) -> None:
        """Append a finished function_call output item to the tool calls."""
        item = event.item
        if getattr(item, "type", None) != "function_call":
            return
        self.tool_calls.append(
            {
                "call_id": item.call_id,
                "name": item.name,
                "arguments": item.arguments or self.partial_arguments.get(item.id, ""),
            }
        )


def _handle_untyped_error(event) -> None:
    """Raise for an untyped event carrying an error payload, else skip it."""
    message = getattr(event, "message", None)
    code = getattr(event, "code", None)
    if message or code:
        raise RuntimeError(f"{code}: {message}" if code else message)
    # Unknown untyped event with no error payload: skip it.


def _raise_failed_error(event) -> None:
    """Raise the provider error carried by a response.failed event."""
    error = event.response.error
    message = error.message if error and error.message else "Response failed"
    raise RuntimeError(message)


# ---------------------------------------------------------------------------
# Backward-compatibility delegators.
#
# ``_consume_response_stream`` is the main entry point (exercised by the
# tests).  The ``_handle_*`` functions are only re-exported from
# ``conversations_api`` for backward compatibility; they remain functional by
# bridging a caller-supplied ``state`` dict to a consumer instance.
# ---------------------------------------------------------------------------

_STATE_KEYS = (
    "content",
    "reasoning",
    "tool_calls",
    "partial_arguments",
    "usage_info",
    "response_id",
)


def _consumer_from_state(state: dict[str, Any]) -> ResponsesStreamConsumer:
    """Build a consumer seeded from a legacy ``state`` dict."""
    consumer = ResponsesStreamConsumer()
    for key in _STATE_KEYS:
        if key in state:
            setattr(consumer, key, state[key])
    return consumer


def _state_from_consumer(
    consumer: ResponsesStreamConsumer, state: dict[str, Any]
) -> None:
    """Write a consumer's parts back into a legacy ``state`` dict."""
    for key in _STATE_KEYS:
        state[key] = getattr(consumer, key)


def _consume_response_stream(stream, cancel_event=None):
    """Consume a streaming Responses API response and assemble its parts.

    Returns ``(full_content, reasoning_content, tool_calls, usage_info,
    response_id)`` where ``tool_calls`` is a list of
    ``{"call_id", "name", "arguments"}`` dicts.  See
    :meth:`ResponsesStreamConsumer.consume`.
    """
    return ResponsesStreamConsumer().consume(stream, cancel_event=cancel_event)


def _handle_stream_event(event, state: dict[str, Any]) -> None:
    """Dispatch a single stream event to the matching handler (legacy bridge)."""
    consumer = _consumer_from_state(state)
    consumer.handle_event(event)
    _state_from_consumer(consumer, state)


def _handle_completion_event(event, state: dict[str, Any]) -> None:
    """Record the response id / usage into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_completion_event(event)
    _state_from_consumer(consumer, state)


def _handle_text_delta(event, state: dict[str, Any]) -> None:
    """Collect assistant text / reasoning deltas into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_text_delta(event)
    _state_from_consumer(consumer, state)


def _handle_call_arguments(event, state: dict[str, Any]) -> None:
    """Assemble per-item function_call arguments into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_call_arguments(event)
    _state_from_consumer(consumer, state)


def _handle_output_item(event, state: dict[str, Any]) -> None:
    """Append a finished function_call output item to a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_output_item(event)
    _state_from_consumer(consumer, state)


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


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming Responses API call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls, usage_info,
    response_id)``. Tool schemas are attached here (mirroring
    ``completions_api._stream_response``); the caller builds the remaining
    kwargs per round.

    The effective model's built-in (native) tools (e.g. Alibaba/Qwen's
    ``code_interpreter`` / ``web_search`` / ``web_extractor``) are resolved
    per model in ``responses_state._build_call_kwargs`` and carried in
    ``call_kwargs`` under the reserved ``_builtin_tools`` key as Responses
    entries (``{"type": ...}``, already in the Responses format -- they must
    not go through the function-schema conversion).  They are merged after
    the converted function-tool schemas, mirroring the web agent; the key is
    popped before the API call so it never reaches the server.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    builtin_tools = call_kwargs.pop("_builtin_tools", None) or []
    tools = list(tools_schemas or []) + list(builtin_tools)
    if tools:
        logger.debug(f"Calling Responses API (streaming) with {len(tools)} tools")
        stream = client.responses.create(
            **call_kwargs,
            tools=tools,
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
