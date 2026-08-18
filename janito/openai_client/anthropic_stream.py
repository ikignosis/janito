"""
Stream consumption for the native Anthropic Messages API.

These helpers are used by :mod:`janito.openai_client.anthropic_api`, which
talks to ``client.messages.create`` with streaming enabled.  The Messages API
streams typed events; blocks (text, thinking, tool_use) arrive as
``content_block_start`` / ``content_block_delta`` / ``content_block_stop``
triples, so each block is assembled per index and flushed when it stops, and
``message_stop`` is the terminal event.

:class:`AnthropicStreamConsumer` is the real implementation: it holds the
assembled response parts as instance attributes (no ``state`` dict plumbing)
and drives the per-event handlers.  The module-level ``_consume_stream`` /
``_handle_*`` functions are thin delegators kept for backward compatibility
(they are re-exported from ``anthropic_api``).
"""

import json
import logging
from types import SimpleNamespace
from typing import Any

from .client_support import _extract_raw_attrs

# Configure logger for this module
logger = logging.getLogger(__name__)


class AnthropicStreamConsumer:
    """Assemble Anthropic Messages stream events into a single response.

    The consumer owns the accumulated text / reasoning content, the finished
    ``tool_use`` blocks, the per-index in-flight blocks, the input/output
    token counts and the raw top-level response metadata.  :meth:`consume`
    drives the stream and returns the response parts; the ``handle_*``
    methods apply individual events.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_use_blocks: list[dict[str, Any]] = []
        # index -> {type, text, id, name, json} while a block is in flight
        self.blocks: dict[int, dict[str, Any]] = {}
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.raw_attrs: dict[str, Any] = {}
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

    @property
    def usage_info(self) -> Any:
        """A ``SimpleNamespace`` usage object, or ``None`` when the API
        reported no usage (``input_tokens``/``output_tokens`` both unset)."""
        if self.input_tokens is None and self.output_tokens is None:
            return None
        return SimpleNamespace(
            total_tokens=(self.input_tokens or 0) + (self.output_tokens or 0),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def consume(self, stream, cancel_event=None):
        """Consume a streaming Anthropic Messages response and assemble its parts.

        Returns ``(full_content, reasoning_content, tool_use_blocks,
        usage_info, raw_attrs)`` where ``tool_use_blocks`` is a list of
        ``{"id", "name", "input"}`` dicts (``input`` is the parsed JSON
        argument object), ``usage_info`` is a ``SimpleNamespace`` with
        ``total_tokens``/``input_tokens``/``output_tokens`` and ``raw_attrs``
        holds the raw top-level response metadata (id, model, role,
        stop_reason, ...).

        When ``cancel_event`` is set (user pressed Enter while waiting), the
        stream is abandoned as soon as the next event arrives.
        """
        for event in stream:
            self._events_seen += 1
            # Honour an Enter-to-cancel request: stop consuming as soon as the
            # next event arrives so the worker can close the connection.
            if cancel_event is not None and cancel_event.is_set():
                break
            if self.handle_event(event):
                break

        # A healthy stream always ends with message_stop; a stream with zero
        # events means the API failed before producing anything. Fail loudly
        # instead of returning an empty answer. An Enter-to-cancel
        # short-circuit must not be treated as an empty stream.
        if self._events_seen == 0 and (
            cancel_event is None or not cancel_event.is_set()
        ):
            raise RuntimeError(
                "The Anthropic API returned no stream events (empty response)."
            )
        return (
            self.full_content,
            self.reasoning_content,
            self.tool_use_blocks,
            self.usage_info,
            self.raw_attrs,
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_event(self, event) -> bool:
        """Dispatch one stream event; return True when the stream is complete."""
        event_type = getattr(event, "type", None)
        if event_type == "message_start":
            self.handle_message_start(event)
        elif event_type == "content_block_start":
            self.handle_content_block_start(event)
        elif event_type == "content_block_delta":
            self.handle_content_block_delta(event)
        elif event_type == "content_block_stop":
            self.handle_content_block_stop(event)
        elif event_type == "message_delta":
            self.handle_message_delta(event)
        elif event_type == "message_stop":
            # Terminal event: the response is fully consumed.
            return True
        elif event_type == "error":
            _raise_anthropic_error(event)
        return False

    def handle_message_start(self, event) -> None:
        """Record the input tokens and the raw message metadata."""
        message = getattr(event, "message", None)
        if message is not None:
            # Raw top-level message metadata (id, model, role, stop_reason,
            # ...) for the verbose dump; content and usage are surfaced
            # elsewhere.
            self.raw_attrs.update(
                _extract_raw_attrs(message, skip=("content", "usage"))
            )
            usage = getattr(message, "usage", None)
            if usage is not None:
                self.input_tokens = getattr(usage, "input_tokens", None)

    def handle_content_block_start(self, event) -> None:
        """Open a new content block indexed by ``index``."""
        index = getattr(event, "index", None)
        if index is None:
            return
        content_block = getattr(event, "content_block", None)
        self.blocks[index] = {
            "type": getattr(content_block, "type", None),
            "text": "",
            "id": getattr(content_block, "id", None),
            "name": getattr(content_block, "name", None),
            "json": "",
        }

    def handle_content_block_delta(self, event) -> None:
        """Accumulate text/thinking/JSON deltas into the in-flight block."""
        index = getattr(event, "index", None)
        block = self.blocks.get(index)
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

    def handle_content_block_stop(self, event) -> None:
        """Flush a finished block into content, reasoning or tool_use_blocks."""
        index = getattr(event, "index", None)
        block = self.blocks.pop(index, None)
        if block is None:
            return
        if block["type"] == "text":
            self.content.append(block["text"])
        elif block["type"] == "thinking":
            if block["text"]:
                self.reasoning.append(block["text"])
        elif block["type"] == "tool_use":
            self.tool_use_blocks.append(_parse_tool_use_block(block))

    def handle_message_delta(self, event) -> None:
        """Record the output tokens and the raw stop_reason."""
        usage = getattr(event, "usage", None)
        if usage is not None:
            self.output_tokens = getattr(usage, "output_tokens", None)
        delta = getattr(event, "delta", None)
        if delta is not None:
            stop_reason = getattr(delta, "stop_reason", None)
            if stop_reason:
                self.raw_attrs["stop_reason"] = stop_reason


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


def _raise_anthropic_error(event) -> None:
    """Raise the error message carried by an error event."""
    error = getattr(event, "error", None)
    if isinstance(error, dict):
        message = error.get("message")
    else:
        message = getattr(error, "message", None)
    raise RuntimeError(message or "Anthropic API error")


# ---------------------------------------------------------------------------
# Backward-compatibility delegators (re-exported from ``anthropic_api``).
# ---------------------------------------------------------------------------

_STATE_KEYS = (
    "content",
    "reasoning",
    "tool_use_blocks",
    "blocks",
    "input_tokens",
    "output_tokens",
    "raw_attrs",
)


def _consumer_from_state(state: dict[str, Any]) -> AnthropicStreamConsumer:
    """Build a consumer seeded from a legacy ``state`` dict."""
    consumer = AnthropicStreamConsumer()
    for key in _STATE_KEYS:
        if key in state:
            setattr(consumer, key, state[key])
    return consumer


def _state_from_consumer(
    consumer: AnthropicStreamConsumer, state: dict[str, Any]
) -> None:
    """Write a consumer's parts back into a legacy ``state`` dict."""
    for key in _STATE_KEYS:
        state[key] = getattr(consumer, key)


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming Anthropic Messages response and assemble its parts.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info,
    raw_attrs)``.  See :meth:`AnthropicStreamConsumer.consume`.
    """
    return AnthropicStreamConsumer().consume(stream, cancel_event=cancel_event)


def _handle_anthropic_event(event, state: dict[str, Any]) -> bool:
    """Dispatch one stream event into a legacy state dict; True when complete."""
    consumer = _consumer_from_state(state)
    complete = consumer.handle_event(event)
    _state_from_consumer(consumer, state)
    return complete


def _handle_message_start(event, state: dict[str, Any]) -> None:
    """Record the input tokens into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_message_start(event)
    _state_from_consumer(consumer, state)


def _handle_content_block_start(event, state: dict[str, Any]) -> None:
    """Open a new content block in a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_content_block_start(event)
    _state_from_consumer(consumer, state)


def _handle_content_block_delta(event, state: dict[str, Any]) -> None:
    """Accumulate a content-block delta into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_content_block_delta(event)
    _state_from_consumer(consumer, state)


def _handle_content_block_stop(event, state: dict[str, Any]) -> None:
    """Flush a finished content block in a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_content_block_stop(event)
    _state_from_consumer(consumer, state)


def _handle_message_delta(event, state: dict[str, Any]) -> None:
    """Record the output tokens into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_message_delta(event)
    _state_from_consumer(consumer, state)


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


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming Anthropic Messages call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info,
    raw_attrs)``.  Tool schemas are attached here (mirroring ``completions_api._stream_response``);
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
