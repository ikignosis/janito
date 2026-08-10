"""Native DashScope SDK runner for the web agentic loop.

The per-API adapter (call-kwargs building, stream accumulation) lives in
:mod:`janito.agent.dashscope` — the shared adapter layer used by both agent
loops.  This module keeps the web-only glue: :func:`create_client`
(prepares the sync DashScope SDK), :func:`_dashscope_chunks` (consumes the
sync stream chunk-by-chunk through ``asyncio.to_thread``, retrying once on
a model/endpoint mismatch) and :func:`stream_turn_events`.
"""

import asyncio
import importlib.util
import logging
from types import SimpleNamespace

from janito.agent.dashscope import (  # noqa: F401
    DashScopeTurnAccumulator,
    _get,
    accumulator,
    build_call_kwargs,
)
from janito.agent.usage import usage_event_from_usage  # noqa: F401

from ..events import ReasoningEvent, TokenEvent

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
    "_dashscope_chunks",
    "_get",
    "_next_or_none",
    "usage_event_from_usage",
]
