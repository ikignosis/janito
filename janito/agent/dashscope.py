"""Shared native DashScope SDK adapter: kwargs + accumulation.

The DashScope generation-API turn pipeline used to live in the web runner
(``janito.web.backend.agent.dashscope``); the pure parts — call-kwargs
building and stream accumulation — moved here so both agent loops share
them.  The web shim keeps the async glue (:func:`create_client`,
:func:`_dashscope_chunks` and :func:`stream_turn_events`), which consumes
the **sync** DashScope SDK stream chunk-by-chunk through
``asyncio.to_thread``.

The ``dashscope`` package is **optional** (see
``janito.provider_data.REQUIRES_BY_API_TYPE``); importing it happens lazily
inside :func:`create_client` (kept in the web shim), so importing this
module never requires it.

**Conversation model.** The DashScope generation API is stateless and accepts
the OpenAI chat message shape natively (``system``/``user``/``assistant``/
``tool`` with ``tool_calls``), so the session history is sent as-is; the
multimodal endpoint's content-list conversion is applied per round by the
stream opener (mirroring ``janito.openai_client.dashscope_stream``).
"""

import logging
from types import SimpleNamespace

from .usage import usage_event_from_usage

logger = logging.getLogger(__name__)


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


class DashScopeTurnAccumulator:
    """Fold DashScope generation stream chunks into one turn's collected state.

    Implements the same interface as
    :class:`~janito.agent.completions.CompletionsAccumulator` (``handle`` ->
    ``(reasoning_delta, content_delta)`` plus the end-of-turn accessors).
    With ``incremental_output=True`` each chunk carries only the newly
    generated text, so deltas are forwarded to the browser as they arrive;
    tool-call arguments (a JSON string split across chunks) are accumulated
    by index and exposed in the OpenAI wire format.
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


__all__ = [
    "DashScopeTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "_get",
]
