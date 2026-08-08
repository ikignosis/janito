"""Native DashScope SDK runner for the web agentic loop.

This module is the ``"DashScope"`` counterpart of the Completions path in
``call.py``: it prepares the native DashScope SDK, builds the per-turn
``Generation.call`` / ``MultiModalConversation.call`` kwargs, and streams the
chunks while yielding reasoning/token events to the browser.

The ``dashscope`` package is **optional** (see
``janito.provider_config.REQUIRES_BY_API_TYPE``); importing it happens lazily
inside :func:`create_client` so importing the web backend never requires it,
mirroring ``janito.dashscope_api``.

**Sync SDK, async loop.** The DashScope SDK is synchronous, so the stream
generator is consumed chunk-by-chunk through ``asyncio.to_thread`` -- the
event loop stays free and the tokens keep streaming live to the browser.

**Conversation model.** The DashScope generation API is stateless and accepts
the OpenAI chat message shape natively (``system``/``user``/``assistant``/
``tool`` with ``tool_calls``), so the session history is sent as-is; the
multimodal endpoint's content-list conversion is applied per round by the
stream opener (mirroring ``janito.openai_client.dashscope_stream``).
"""

import asyncio
import importlib.util
import logging
from types import SimpleNamespace

from ..events import ReasoningEvent, TokenEvent
from .call import usage_event_from_usage

logger = logging.getLogger(__name__)


def create_client(base_url, api_key):
    """Prepare the native DashScope SDK, guarding the optional package.

    The DashScope SDK routes requests through the module-level
    ``base_http_api_url`` global; it is pointed at the resolved endpoint
    (the provider's native-SDK base URL, or a config endpoint override)
    before the first call.  Returns a lightweight handle carrying the
    resolved ``base_url`` / ``api_key`` for the stream runner.
    """
    if importlib.util.find_spec("dashscope") is None:
        raise RuntimeError(
            "API type 'DashScope' requires the optional 'dashscope' package, "
            "which is not installed. Install it with: pip install dashscope"
        )
    import dashscope

    if base_url:
        dashscope.base_http_api_url = base_url
        logger.debug(f"DashScope base_http_api_url set to {base_url}")

    return SimpleNamespace(base_url=base_url, api_key=api_key)


def build_call_kwargs(
    model: str,
    messages: list[dict],
    tools_schemas: list[dict] | None,
    config,
    max_output_tokens: int | None,
    preserve_thinking,
    reasoning_level: str | None,
) -> dict:
    """Build the DashScope generation kwargs for one turn.

    Mirrors ``janito.dashscope_api._build_call_kwargs`` (``result_format``,
    streaming, incremental output, ``enable_thinking``).  The OpenAI-format
    ``messages`` history is sent as-is -- the native API accepts that shape.
    ``preserve_thinking`` / ``reasoning_level`` are accepted for signature
    parity but are not used by the native SDK (like the CLI client).
    """
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    call_kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_output_tokens,
        "result_format": "message",
        "stream": True,
        "incremental_output": True,
    }
    # Enable thinking mode for Qwen models that support it (Alibaba/Qwen
    # reason by default).  Only set when True so models that always reason
    # keep their own default.
    if config.effective_thinking:
        call_kwargs["enable_thinking"] = True
    if tools_schemas:
        call_kwargs["tools"] = tools_schemas
    return call_kwargs


def _get(obj, key: str, default=None):
    """Read a key from a DashScope SDK object (DictMixin: dict- or attr-style)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _next_or_none(gen):
    """``next(gen)`` that returns ``None`` at exhaustion (for ``to_thread``)."""
    try:
        return next(gen)
    except StopIteration:
        return None


async def _dashscope_chunks(handle, call_kwargs: dict):
    """Yield chunks from the sync DashScope stream, off the event loop.

    The native API serves multimodal models (e.g. the alibaba default
    ``qwen3.8-max``) from the ``multimodal-generation`` endpoint and
    plain-text models from ``text-generation``; the endpoint is inferred from
    the model name and, when the API rejects the model with the "url error"
    (model/endpoint mismatch), the call is retried once on the other endpoint
    so misclassified models still work (mirrors
    ``janito.openai_client.dashscope_stream._stream_response``).
    """
    from dashscope import Generation, MultiModalConversation

    from janito.openai_client.dashscope_stream import (
        _is_multimodal_model,
        _ModelEndpointMismatch,
        _to_multimodal_messages,
    )

    kwargs = dict(call_kwargs)
    kwargs["api_key"] = handle.api_key

    multimodal = _is_multimodal_model(kwargs.get("model", ""))
    attempts = (multimodal, not multimodal)

    last_error: Exception | None = None
    for use_multimodal in attempts:
        round_kwargs = dict(kwargs)
        if use_multimodal:
            # The multimodal API expects message content as a list of
            # modality items ([{"text": "..."}]) instead of a plain string.
            round_kwargs["messages"] = _to_multimodal_messages(round_kwargs["messages"])
        cls = MultiModalConversation if use_multimodal else Generation
        try:
            stream = cls.call(**round_kwargs)
            while True:
                chunk = await asyncio.to_thread(_next_or_none, stream)
                if chunk is None:
                    return
                yield chunk
        except _ModelEndpointMismatch as e:
            last_error = e
            if use_multimodal == attempts[-1]:
                raise
            logger.debug(
                "DashScope rejected the model for this endpoint; retrying on the other generation endpoint"
            )
    raise last_error


class DashScopeTurnAccumulator:
    """Fold DashScope generation stream chunks into one turn's collected state.

    Implements the same interface as :class:`~janito.web.backend.agent.call.StreamAccumulator`
    (``handle`` -> ``(reasoning_delta, content_delta)`` plus the end-of-turn
    accessors).  With ``incremental_output=True`` each chunk carries only the
    newly generated text, so deltas are forwarded to the browser as they
    arrive; tool-call arguments (a JSON string split across chunks) are
    accumulated by index and exposed in the OpenAI wire format.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: dict[int, dict[str, str]] = {}
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.total_tokens: int | None = None
        self.done: bool = False

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def handle(self, chunk) -> tuple[str | None, str | None]:
        """Process one chunk; returns ``(reasoning_delta, content_delta)``."""
        status_code = _get(chunk, "status_code")
        if status_code is not None and status_code != 200:
            self._raise_error(chunk, status_code)

        output = _get(chunk, "output") or {}
        choices = _get(output, "choices") or []
        if not choices:
            # Keep consuming: the terminal chunk may still carry usage.
            self._consume_usage(chunk)
            return None, None

        choice = choices[0]
        message = _get(choice, "message") or {}

        content = _get(message, "content") or ""
        if isinstance(content, list):
            # Multimodal responses carry content as a list of modality items
            # (e.g. [{"text": "..."}]); join the text parts.
            content = "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        reasoning = _get(message, "reasoning_content") or ""

        for tc in _get(message, "tool_calls") or []:
            self._handle_tool_call(tc)
        self._consume_usage(chunk)

        if _get(choice, "finish_reason") == "stop":
            self.done = True

        if content:
            self.content.append(content)
        if reasoning:
            self.reasoning.append(reasoning)
        return (reasoning or None), (content or None)

    def _handle_tool_call(self, tc) -> None:
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

    def _consume_usage(self, chunk) -> None:
        """Keep the most recent usage reported by the API."""
        usage = _get(chunk, "usage")
        if usage is not None:
            self.input_tokens = _get(usage, "input_tokens", self.input_tokens)
            self.output_tokens = _get(usage, "output_tokens", self.output_tokens)
            self.total_tokens = _get(usage, "total_tokens", self.total_tokens)

    def _raise_error(self, chunk, status_code: int) -> None:
        """Raise a DashScope API error, signalling endpoint mismatches."""
        code = _get(chunk, "code") or ""
        message = _get(chunk, "message") or "DashScope API error"
        request_id = _get(chunk, "request_id") or ""
        detail = f" (request_id={request_id})" if request_id else ""
        if code == "InvalidParameter" and "url error" in message:
            # The model was sent to the wrong generation endpoint
            # (multimodal vs text): signal the stream opener to retry once on
            # the other endpoint.
            from janito.openai_client.dashscope_stream import _ModelEndpointMismatch

            raise _ModelEndpointMismatch(
                f"DashScope API error (code={code}): {message}{detail}"
            )
        raise RuntimeError(f"DashScope API error (code={code}): {message}{detail}")

    # ------------------------------------------------------------------
    # End-of-turn assembly
    # ------------------------------------------------------------------

    def full_content(self) -> str:
        return "".join(self.content)

    def reasoning_content(self) -> str | None:
        return "".join(self.reasoning) if self.reasoning else None

    def tool_calls_list(self) -> list[dict]:
        """Assembled tool calls in OpenAI wire format (for ``run_tool_turn``)."""
        return [
            {
                "id": self.tool_calls[idx]["id"],
                "type": "function",
                "function": {
                    "name": self.tool_calls[idx]["name"],
                    "arguments": self.tool_calls[idx]["arguments"] or "{}",
                },
            }
            for idx in sorted(self.tool_calls)
        ]

    def usage_event(self, max_tokens: int | None = None):
        if (
            self.input_tokens is None
            and self.output_tokens is None
            and self.total_tokens is None
        ):
            return None
        usage = SimpleNamespace(
            total_tokens=self.total_tokens,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )
        return usage_event_from_usage(usage, max_tokens)


# Uniform runner interface (used by loop.py): the accumulator class is
# exposed as ``accumulator`` so every API-type runner has the same shape.
accumulator = DashScopeTurnAccumulator


async def stream_turn_events(client, call_kwargs: dict, acc: DashScopeTurnAccumulator):
    """Stream one DashScope generation turn, yielding reasoning/token events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly (``run_tool_turn`` / ``DoneEvent``).
    """
    async for chunk in _dashscope_chunks(client, call_kwargs):
        reasoning_delta, content_delta = acc.handle(chunk)
        if reasoning_delta:
            yield ReasoningEvent(content=reasoning_delta)
        if content_delta:
            yield TokenEvent(content=content_delta)
        if acc.done:
            break


__all__ = [
    "DashScopeTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "create_client",
    "stream_turn_events",
]
