"""
Stream consumption for the Chat Completions API.

These helpers are shared by the OpenAI-compatible clients that talk to
``client.chat.completions.create`` with streaming enabled.  They assemble the
streamed deltas (content, reasoning/thinking text and tool-call arguments,
which arrive split across many chunks) into a single response.

:class:`CompletionsStreamConsumer` is the real implementation: it holds the
assembled response parts as instance attributes (no ``state`` dict plumbing)
and drives the per-chunk handlers.  The module-level ``_consume_stream`` /
``_consume_chunk`` / ``_consume_tool_call_delta`` functions are thin
delegators kept for backward compatibility (they are re-exported from
``completions_api``).
"""

import logging

# Configure logger for this module
logger = logging.getLogger(__name__)


class CompletionsStreamConsumer:
    """Assemble Chat Completions stream chunks into a single response.

    The consumer owns the accumulated content / reasoning text and the
    per-index tool-call map (arguments arrive split across many chunks, so
    they are accumulated by ``index``).  :meth:`consume` drives the stream
    and returns the response parts; the ``handle_*`` methods apply individual
    chunks/deltas.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: dict[int, dict[str, str]] = {}
        self.usage_info = None

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

    def consume(self, stream):
        """Consume a streaming completion and assemble the response parts.

        Returns ``(full_content, reasoning_content, tool_calls_map,
        usage_info)`` where ``tool_calls_map`` maps call index ->
        ``{id, name, arguments}``.
        """
        for chunk in stream:
            # Usage stats arrive in the final chunk when include_usage is set
            if hasattr(chunk, "usage") and chunk.usage:
                self.usage_info = chunk.usage

            if not chunk.choices:
                continue

            self.handle_chunk(chunk.choices[0].delta)

        return (
            self.full_content,
            self.reasoning_content,
            self.tool_calls,
            self.usage_info,
        )

    # ------------------------------------------------------------------
    # Chunk handlers
    # ------------------------------------------------------------------

    def handle_chunk(self, delta) -> None:
        """Accumulate content, reasoning and tool-call deltas from one chunk."""
        # Collect reasoning / thinking content (DeepSeek R1, OpenAI o1/o3, ...)
        for attr in ("reasoning_content", "reasoning"):
            val = getattr(delta, attr, None)
            if val:
                self.reasoning.append(val)
                break

        # Accumulate main content silently
        if delta.content:
            self.content.append(delta.content)

        # Accumulate tool-call deltas (split across many chunks)
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc_delta in delta.tool_calls:
                self.handle_tool_call_delta(tc_delta)

    def handle_tool_call_delta(self, tc_delta) -> None:
        """Merge one tool-call delta into the per-index tool call map."""
        idx = tc_delta.index
        if idx not in self.tool_calls:
            self.tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
        if tc_delta.id:
            self.tool_calls[idx]["id"] = tc_delta.id
        if tc_delta.function:
            if tc_delta.function.name:
                self.tool_calls[idx]["name"] = tc_delta.function.name
            if tc_delta.function.arguments:
                self.tool_calls[idx]["arguments"] += tc_delta.function.arguments


# ---------------------------------------------------------------------------
# Backward-compatibility delegators (re-exported from ``completions_api``).
# ---------------------------------------------------------------------------


def _consume_stream(stream):
    """Consume a streaming completion and assemble the response parts.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.
    See :meth:`CompletionsStreamConsumer.consume`.
    """
    return CompletionsStreamConsumer().consume(stream)


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


def _stream_response(client, call_kwargs, tools_schemas):
    """Open a streaming completion and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls_map, usage_info)``.
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

    return _consume_stream(stream)
