"""
Stream consumption for the native DashScope generation API.

These helpers are used by :mod:`janito.dashscope_api`, which talks to the
native DashScope SDK (``Generation.call`` / ``MultiModalConversation.call``)
with streaming enabled.  They handle both the text-generation and
multimodal-generation endpoints, accumulate tool-call arguments split across
chunks, and honour the Enter-to-cancel ``cancel_event``.

:class:`DashScopeStreamConsumer` is the real implementation: it holds the
assembled response parts as instance attributes (no ``state`` dict plumbing)
and drives the per-chunk handlers.  The module-level ``_consume_stream`` /
``_consume_*`` functions are thin delegators kept for backward compatibility
(they are re-exported from ``dashscope_api``).
"""

import logging
import re
from types import SimpleNamespace
from typing import Any

# Configure logger for this module
logger = logging.getLogger(__name__)


class _ModelEndpointMismatch(RuntimeError):
    """Raised when the DashScope API rejects a model for the chosen endpoint.

    The native DashScope API serves models from two generation endpoints:
    ``text-generation`` (``Generation.call``) for plain-text models and
    ``multimodal-generation`` (``MultiModalConversation.call``) for multimodal
    models.  Sending a model to the wrong endpoint fails with
    ``InvalidParameter: url error, please check url``.  ``_stream_response``
    catches this to retry once on the other endpoint.
    """


def _is_multimodal_model(model: str) -> bool:
    """Return True when a DashScope model is served by the multimodal endpoint.

    The DashScope native API serves plain-text models (``qwen-plus``,
    ``qwen-flash``, ``qwen3-max``, ``qwen3.7-max``, ...) from the
    ``text-generation`` endpoint (``Generation.call``) and multimodal models
    (Qwen-VL / Qwen-Omni, the ``qwen3.x-plus`` generation, and the
    ``qwen3.8-max`` flagship) from the ``multimodal-generation`` endpoint
    (``MultiModalConversation.call``).  Calling a model on the wrong endpoint
    fails with ``InvalidParameter: url error, please check url``.

    This is a best-effort heuristic: when it misclassifies a model,
    ``_stream_response`` retries once on the other endpoint.
    """
    name = (model or "").strip().lower()
    if not name:
        return False
    # Vision / omni model families are multimodal by naming convention.
    if "-vl" in name or "omni" in name:
        return True
    # The qwen3.x-plus generation and the qwen3.8-max flagship are served by
    # the multimodal-generation endpoint, while the qwen3.x-max text models
    # (e.g. qwen3.7-max) are not.
    if re.match(r"^qwen3\.\d+-plus$", name) or name == "qwen3.8-max":
        return True
    return False


def _to_multimodal_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert plain-string message content to DashScope multimodal form.

    The multimodal-generation API expects every message ``content`` to be a
    list of modality items (``[{"text": "..."}]``) instead of a plain string.
    Returns a shallow copy with string contents wrapped; other fields
    (``tool_calls``, ``tool_call_id``, ``reasoning_content``) are kept as-is.
    """
    converted = []
    for message in messages:
        message = dict(message)
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = [{"text": content}]
        converted.append(message)
    return converted


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from a DashScope SDK object (DictMixin: dict- or attr-style).

    The DashScope SDK response/message objects are ``DictMixin`` instances,
    which support both attribute access (``resp.output``) and mapping access
    (``resp["output"]``).  Some fields (e.g. ``tool_calls``) are plain dicts.
    This helper abstracts over both so the stream consumer stays robust.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class DashScopeStreamConsumer:
    """Assemble DashScope generation stream chunks into a single response.

    Works for both the text-generation (``Generation.call``) and
    multimodal-generation (``MultiModalConversation.call``) streams.  The
    consumer owns the accumulated content / reasoning text, the per-index
    tool-call map, the usage counters and the finish flag.  :meth:`consume`
    drives the stream and returns the response parts; the ``handle_*``
    methods apply individual chunks/messages.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        # index -> {id, name, arguments}
        self.tool_calls: dict[int, dict[str, str]] = {}
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.total_tokens: int | None = None
        self.finish: bool = False
        self._chunks_seen = 0

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
    def usage_state(self) -> dict[str, Any]:
        """The usage counters as a dict (for ``_build_usage_info``)."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def consume(self, stream, cancel_event=None):
        """Consume a streaming DashScope generation response.

        Returns ``(full_content, reasoning_content, tool_use_blocks,
        usage_info)`` where ``tool_use_blocks`` is a list of
        ``{"id", "name", "arguments"}`` dicts (``arguments`` is the raw JSON
        string from the model) and ``usage_info`` is a ``SimpleNamespace``
        with ``total_tokens``/``input_tokens``/``output_tokens`` (``None``
        when the API reported no usage).

        With ``incremental_output=True`` (set by the caller) each chunk
        carries only the newly generated text, so content / reasoning deltas
        are accumulated.  Multimodal responses carry ``content`` as a list of
        modality items (``[{"text": "..."}]``), which is joined here.  The
        terminal chunk reports ``finish_reason == "stop"``; tool-call requests
        stream across many chunks (the ``arguments`` JSON is split), so they
        are accumulated by ``index``.

        When ``cancel_event`` is set (user pressed Enter while waiting), the
        stream is abandoned as soon as the next chunk arrives.
        """
        for chunk in stream:
            self._chunks_seen += 1
            # Honour an Enter-to-cancel request: stop consuming as soon as the
            # next chunk arrives so the worker can close the connection.
            if cancel_event is not None and cancel_event.is_set():
                break
            self.handle_chunk(chunk)
            if self.finish:
                break

        # A healthy stream always ends with a chunk whose finish_reason is
        # "stop"; a stream with zero chunks means the API failed before
        # producing anything.  Fail loudly instead of returning an empty
        # answer.  An Enter-to-cancel short-circuit must not be treated as an
        # empty stream.
        if self._chunks_seen == 0 and (
            cancel_event is None or not cancel_event.is_set()
        ):
            raise RuntimeError(
                "The DashScope API returned no stream chunks (empty response)."
            )
        tool_use_blocks = _build_tool_use_blocks(self.tool_calls)
        return (
            self.full_content,
            self.reasoning_content,
            tool_use_blocks,
            _build_usage_info(self.usage_state),
        )

    # ------------------------------------------------------------------
    # Chunk handlers
    # ------------------------------------------------------------------

    def handle_chunk(self, chunk) -> None:
        """Process one stream chunk."""
        status_code = _get(chunk, "status_code")
        if status_code is not None and status_code != 200:
            _raise_dashscope_error(chunk, status_code)

        output = _get(chunk, "output") or {}
        choices = _get(output, "choices") or []
        if not choices:
            # Keep consuming: the terminal chunk may still carry usage.
            self.consume_usage(chunk)
            return

        choice = choices[0]
        message = _get(choice, "message") or {}
        self.handle_message(message)
        self.consume_usage(chunk)

        if _get(choice, "finish_reason") == "stop":
            self.finish = True

    def handle_message(self, message) -> None:
        """Accumulate content, reasoning and tool-call deltas from one message."""
        content = _get(message, "content") or ""
        if isinstance(content, list):
            # Multimodal responses carry content as a list of modality items
            # (e.g. [{"text": "..."}]); join the text parts.
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        if content:
            self.content.append(content)

        reasoning = _get(message, "reasoning_content") or ""
        if reasoning:
            self.reasoning.append(reasoning)

        # Tool-call requests stream across many chunks: each chunk carries a
        # partial tool_call with an ``index`` and the ``arguments`` JSON is
        # split across chunks, so accumulate by index (mirroring the
        # Completions consumer) instead of appending one block per chunk.
        for tc in _get(message, "tool_calls") or []:
            self.handle_tool_call(tc)

    def handle_tool_call(self, tc) -> None:
        """Merge one DashScope tool-call chunk into the per-index map."""
        idx = _get(tc, "index", 0) or 0
        entry = self.tool_calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
        if _get(tc, "id"):
            entry["id"] = _get(tc, "id")
        function = _get(tc, "function") or {}
        if _get(function, "name"):
            entry["name"] = _get(function, "name")
        arguments = _get(function, "arguments")
        if arguments:
            entry["arguments"] += arguments

    def consume_usage(self, chunk) -> None:
        """Keep the most recent usage reported by the API."""
        usage = _get(chunk, "usage")
        if usage is not None:
            self.input_tokens = _get(usage, "input_tokens", self.input_tokens)
            self.output_tokens = _get(usage, "output_tokens", self.output_tokens)
            self.total_tokens = _get(usage, "total_tokens", self.total_tokens)


def _raise_dashscope_error(chunk, status_code: int) -> None:
    """Raise a DashScope API error, signalling endpoint mismatches."""
    code = _get(chunk, "code") or ""
    message = _get(chunk, "message") or "DashScope API error"
    request_id = _get(chunk, "request_id") or ""
    detail = f" (request_id={request_id})" if request_id else ""
    if code == "InvalidParameter" and "url error" in message:
        # The model was sent to the wrong generation endpoint
        # (multimodal vs text).  Signal the caller to retry once on
        # the other endpoint.
        raise _ModelEndpointMismatch(
            f"DashScope API error (code={code}): {message}{detail}"
        )
    raise RuntimeError(f"DashScope API error (code={code}): {message}{detail}")


def _build_tool_use_blocks(
    tool_calls_map: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    """Flatten the accumulated tool calls into a sorted block list."""
    return [
        {
            "id": tool_calls_map[idx]["id"],
            "name": tool_calls_map[idx]["name"],
            "arguments": tool_calls_map[idx]["arguments"] or "{}",
        }
        for idx in sorted(tool_calls_map)
    ]


def _build_usage_info(state: dict[str, Any]) -> Any:
    """Build the usage SimpleNamespace when the API reported usage."""
    if (
        state["input_tokens"] is not None
        or state["output_tokens"] is not None
        or state["total_tokens"] is not None
    ):
        return SimpleNamespace(
            total_tokens=state["total_tokens"],
            input_tokens=state["input_tokens"],
            output_tokens=state["output_tokens"],
        )
    return None


# ---------------------------------------------------------------------------
# Backward-compatibility delegators (re-exported from ``dashscope_api``).
# ---------------------------------------------------------------------------

_STATE_KEYS = (
    "content",
    "reasoning",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "finish",
)


def _consumer_from_state(state: dict[str, Any]) -> DashScopeStreamConsumer:
    """Build a consumer seeded from a legacy ``state`` dict."""
    consumer = DashScopeStreamConsumer()
    for key in _STATE_KEYS:
        if key in state:
            setattr(consumer, key, state[key])
    return consumer


def _state_from_consumer(
    consumer: DashScopeStreamConsumer, state: dict[str, Any]
) -> None:
    """Write a consumer's parts back into a legacy ``state`` dict."""
    for key in _STATE_KEYS:
        state[key] = getattr(consumer, key)


def _consume_stream(stream, cancel_event=None):
    """Consume a streaming DashScope generation response.

    See :meth:`DashScopeStreamConsumer.consume` for the return shape.
    """
    return DashScopeStreamConsumer().consume(stream, cancel_event=cancel_event)


def _consume_dashscope_chunk(chunk, state: dict[str, Any]) -> None:
    """Process one stream chunk into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_chunk(chunk)
    _state_from_consumer(consumer, state)


def _consume_message(message, state: dict[str, Any]) -> None:
    """Accumulate one message's deltas into a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.handle_message(message)
    _state_from_consumer(consumer, state)


def _consume_tool_call(tc, tool_calls_map: dict[int, dict[str, str]]) -> None:
    """Merge one tool-call chunk into a legacy per-index map (in-place)."""
    consumer = DashScopeStreamConsumer()
    consumer.tool_calls = tool_calls_map
    consumer.handle_tool_call(tc)


def _consume_usage(chunk, state: dict[str, Any]) -> None:
    """Keep the most recent usage in a legacy state dict."""
    consumer = _consumer_from_state(state)
    consumer.consume_usage(chunk)
    _state_from_consumer(consumer, state)


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a streaming DashScope generation call and fully consume it.

    Returns ``(full_content, reasoning_content, tool_use_blocks, usage_info)``.
    Tool schemas are attached here (mirroring ``completions_api._stream_response``);
    the caller builds the remaining kwargs per round.

    The native DashScope API serves multimodal models (e.g. the alibaba
    default ``qwen3.8-max``) from the ``multimodal-generation`` endpoint
    (``MultiModalConversation``) and plain-text models from
    ``text-generation`` (``Generation``).  The endpoint is inferred from the
    model name; when the API rejects the model with the "url error"
    (model/endpoint mismatch), the call is retried once on the other
    endpoint so misclassified models still work.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned and the underlying connection is closed.
    """
    from dashscope import Generation, MultiModalConversation

    kwargs = dict(call_kwargs)
    kwargs["api_key"] = client.api_key
    if tools_schemas:
        logger.debug(
            f"Calling DashScope Generation API (streaming) with {len(tools_schemas)} tools"
        )
        kwargs["tools"] = tools_schemas
    else:
        logger.debug("Calling DashScope Generation API (streaming) without tools")

    multimodal = _is_multimodal_model(kwargs.get("model", ""))
    attempts = (multimodal, not multimodal)

    for use_multimodal in attempts:
        round_kwargs = dict(kwargs)
        if use_multimodal:
            # The multimodal API expects message content as a list of
            # modality items ([{"text": "..."}]) instead of a plain string.
            round_kwargs["messages"] = _to_multimodal_messages(round_kwargs["messages"])
        cls = MultiModalConversation if use_multimodal else Generation
        logger.debug(
            "Calling DashScope %s API (streaming) with %d tools",
            "multimodal-generation" if use_multimodal else "text-generation",
            len(tools_schemas),
        )
        stream = cls.call(**round_kwargs)
        try:
            try:
                return _consume_stream(stream, cancel_event=cancel_event)
            except _ModelEndpointMismatch:
                # The API rejected the model for this endpoint; retry once on
                # the other one, unless the user already pressed Enter.
                if cancel_event is not None and cancel_event.is_set():
                    raise
                if use_multimodal == attempts[-1]:
                    raise
                logger.debug(
                    "DashScope rejected the model for this endpoint; "
                    "retrying on the other generation endpoint"
                )
                continue
        finally:
            # Abort the underlying HTTP stream when the user pressed Enter so
            # the connection is released promptly instead of streaming to
            # completion.
            if cancel_event is not None and cancel_event.is_set():
                close = getattr(stream, "close", None)
                if callable(close):
                    close()
