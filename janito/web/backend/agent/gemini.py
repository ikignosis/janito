"""Native Gemini SDK runner for the web agentic loop.

The per-API adapter (call-kwargs building, stream accumulation) lives in
:mod:`janito.agent.gemini` -- the shared adapter layer used by both agent
loops.  This module keeps the web-only glue: :func:`create_client`
(prepares the sync ``google-genai`` client, guarding the optional package)
and :func:`stream_turn_events` (consumes the sync stream chunk-by-chunk
through ``asyncio.to_thread``).
"""

import asyncio
import importlib.util
import logging

from janito.agent.gemini import (  # noqa: F401
    GeminiTurnAccumulator,
    accumulator,
    build_call_kwargs,
)
from janito.agent.usage import usage_event_from_usage  # noqa: F401

from ..events import ReasoningEvent, TokenEvent

logger = logging.getLogger(__name__)


def create_client(base_url, api_key):
    """Create the native Gemini SDK client, guarding the optional package.

    The ``google-genai`` package is optional (see
    ``janito.providers.REQUIRES_BY_API_TYPE``), so its availability is checked
    explicitly with ``importlib.util.find_spec`` and the import happens
    lazily.  The resolved base URL (the provider's native-SDK base URL from
    ``endpoint_by_api_type``, or a config endpoint override) is passed as the
    SDK's ``http_options.base_url``; ``None`` uses the SDK default
    (``https://generativelanguage.googleapis.com``).
    """
    try:
        spec = importlib.util.find_spec("google.genai")
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise RuntimeError(
            "API type 'Gemini' requires the optional 'google-genai' package, "
            "which is not installed. Install it with: pip install google-genai"
        )
    from google import genai

    http_options = {"base_url": base_url} if base_url else None
    return genai.Client(api_key=api_key, http_options=http_options)


def _next_or_none(gen):
    """``next(gen)`` that returns ``None`` at exhaustion (for ``to_thread``)."""
    try:
        return next(gen)
    except StopIteration:
        return None


async def _gemini_chunks(client, call_kwargs: dict):
    """Yield chunks from the sync Gemini stream, off the event loop.

    ``generate_content_stream`` is a sync generator; each chunk is pulled
    through ``asyncio.to_thread`` so the event loop stays responsive while
    the SDK streams the response.
    """
    stream = client.models.generate_content_stream(**call_kwargs)
    while True:
        chunk = await asyncio.to_thread(_next_or_none, stream)
        if chunk is None:
            return
        yield chunk


async def stream_turn_events(client, call_kwargs: dict, acc: GeminiTurnAccumulator):
    """Stream one Gemini generation turn, yielding reasoning/token events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly (``run_tool_turn`` / ``DoneEvent``).
    """
    async for chunk in _gemini_chunks(client, call_kwargs):
        reasoning_delta, content_delta = acc.handle(chunk)
        if reasoning_delta:
            yield ReasoningEvent(content=reasoning_delta)
        if content_delta:
            yield TokenEvent(content=content_delta)
        if acc.done:
            break


__all__ = [
    "GeminiTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "create_client",
    "stream_turn_events",
    "_gemini_chunks",
    "_next_or_none",
    "usage_event_from_usage",
]
