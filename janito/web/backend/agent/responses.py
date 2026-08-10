"""Responses API runner for the web agentic loop.

The per-API adapter (call-kwargs building, history conversion, stream
accumulation) lives in :mod:`janito.agent.responses` — the shared adapter
layer used by both agent loops.  This module keeps the web-only glue:
:func:`create_client` (async SDK client) and :func:`stream_turn_events`
(which drives the stream and yields reasoning/token/image events to the
browser).
"""

import logging

from janito.agent.responses import (  # noqa: F401
    ResponsesTurnAccumulator,
    _convert_tools,
    _messages_to_input_items,
    _model_supports_image_generation,
    _save_base64_image,
    _text_of,
    accumulator,
    build_call_kwargs,
)
from janito.agent.usage import usage_event_from_usage  # noqa: F401

from ..events import ImageEvent, ReasoningEvent, TokenEvent

logger = logging.getLogger(__name__)


def create_client(base_url, api_key):
    """Create the async OpenAI SDK client (base_url may be ``None``)."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def stream_turn_events(client, call_kwargs: dict, acc: ResponsesTurnAccumulator):
    """Stream one Responses turn, yielding reasoning/token/image events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly (``run_tool_turn`` / ``DoneEvent``).  Images
    generated natively by the ``image_generation`` tool are saved to temp
    PNG files by the accumulator and surfaced here as ``ImageEvent``s the
    moment their output item completes (``emitted_images`` tracks the ones
    already yielded so each image is emitted exactly once).
    """
    stream = await client.responses.create(**call_kwargs)
    emitted_images = 0
    async for event in stream:
        reasoning_delta, content_delta = acc.handle(event)
        if reasoning_delta:
            yield ReasoningEvent(content=reasoning_delta)
        if content_delta:
            yield TokenEvent(content=content_delta)
        for img in acc.image_results[emitted_images:]:
            yield ImageEvent(
                path=img["path"],
                revised_prompt=img.get("revised_prompt", ""),
            )
            emitted_images += 1


__all__ = [
    "ResponsesTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "create_client",
    "stream_turn_events",
    "_convert_tools",
    "_messages_to_input_items",
    "_model_supports_image_generation",
    "_save_base64_image",
    "_text_of",
    "usage_event_from_usage",
]
