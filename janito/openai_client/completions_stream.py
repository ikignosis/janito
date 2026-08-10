"""
Stream consumption for the Chat Completions API.

These helpers are shared by the OpenAI-compatible clients that talk to
``client.chat.completions.create`` with streaming enabled.  They assemble the
streamed deltas (content, reasoning/thinking text and tool-call arguments,
which arrive split across many chunks) into a single response.

The per-chunk folding lives in the shared
:class:`~janito.agent.completions.CompletionsAccumulator` (also used by the
web loop's ``StreamAccumulator``); :class:`CompletionsStreamConsumer` adds
the CLI-specific driver — :meth:`consume` walks a sync stream with
Enter-to-cancel support and returns the response parts.  The module-level
``_consume_stream`` / ``_consume_chunk`` / ``_consume_tool_call_delta``
functions are thin delegators kept for backward compatibility (they are
re-exported from ``completions_api``).
"""

import logging

from janito.agent.completions import CompletionsAccumulator

# Configure logger for this module
logger = logging.getLogger(__name__)


class CompletionsStreamConsumer(CompletionsAccumulator):
    """Assemble Chat Completions stream chunks into a single response (CLI).

    The consumer owns the accumulated content / reasoning text and the
    per-index tool-call map (arguments arrive split across many chunks, so
    they are accumulated by ``index``).  :meth:`consume` drives the stream
    and returns the response parts; the ``handle_*`` methods apply individual
    chunks/deltas.
    """

    # The CLI historically exposed the single-delta folding under this name;
    # the shared base calls it ``_fold_tool_call_delta``.
    handle_tool_call_delta = CompletionsAccumulator._fold_tool_call_delta

    @property
    def full_content(self) -> str:
        """The assembled assistant text."""
        return "".join(self.content)

    @property
    def reasoning_content(self) -> str | None:
        """The assembled reasoning text, or ``None`` when none was streamed."""
        return "".join(self.reasoning) if self.reasoning else None

    def handle_chunk(self, delta) -> None:
        """Accumulate content, reasoning and tool-call deltas from one delta.

        Legacy per-delta entry point: the CLI consumed one raw ``delta`` at a
        time before the chunk-level ``handle`` API existed (the web loop and
        the shared ``consume`` driver call ``handle(chunk)`` instead).
        """
        # Collect reasoning / thinking content (DeepSeek R1, OpenAI o1/o3, ...)
        self._handle_reasoning_delta(delta)

        # Accumulate main content silently
        if delta.content:
            self.content.append(delta.content)

        # Accumulate tool-call deltas (split across many chunks)
        self._handle_tool_call_delta(delta)

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def consume(self, stream, cancel_event=None):
        """Consume a streaming completion and assemble the response parts.

        Returns ``(full_content, reasoning_content, tool_calls_map,
        usage_info)`` where ``tool_calls_map`` maps call index ->
        ``{id, name, arguments}``.

        When ``cancel_event`` is set (user pressed Enter while waiting), the
        stream is abandoned as soon as the next chunk arrives.
        """
        for chunk in stream:
            # Honour an Enter-to-cancel request: stop consuming as soon as the
            # next chunk arrives so the worker can close the connection.
            if cancel_event is not None and cancel_event.is_set():
                break
            self.handle(chunk)

        return (
            self.full_content,
            self.reasoning_content,
            self.tool_calls,
            self.usage_info,
        )


# ---------------------------------------------------------------------------
# Backward-compatibility delegators (re-exported from ``completions_api``).
# ---------------------------------------------------------------------------


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming completion and assemble the response parts.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.
    See :meth:`CompletionsStreamConsumer.consume`.
    """
    return CompletionsStreamConsumer().consume(stream, cancel_event=cancel_event)


def _consume_chunk(delta, collected_content, collected_reasoning, tool_calls_map):
    """Accumulate content/reasoning/tool-call deltas from one chunk delta.

    Legacy bridge: aliases the caller-supplied collections to a consumer,
    applies the chunk, and relies on in-place mutation to propagate.
    """
    consumer = CompletionsStreamConsumer()
    consumer.content = collected_content
    consumer.reasoning = collected_reasoning
    consumer.tool_calls = tool_calls_map
    consumer.handle_chunk(delta)


def _consume_tool_call_delta(tc_delta, tool_calls_map):
    """Merge one tool-call delta into a per-index tool call map (legacy bridge)."""
    consumer = CompletionsStreamConsumer()
    consumer.tool_calls = tool_calls_map
    consumer.handle_tool_call_delta(tc_delta)


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
