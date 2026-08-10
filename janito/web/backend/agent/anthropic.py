"""Native Anthropic SDK runner for the web agentic loop.

The per-API adapter (call-kwargs building, history conversion, stream
accumulation) lives in :mod:`janito.agent.anthropic` — the shared adapter
layer used by both agent loops.  This module keeps the web-only glue:
:func:`create_client` (async Anthropic SDK client, lazily importing the
optional ``anthropic`` package) and :func:`stream_turn_events` (which
drives the stream and yields reasoning/token events to the browser).
"""

import importlib.util
import logging

from janito.agent.anthropic import (  # noqa: F401
    AnthropicTurnAccumulator,
    _convert_tools,
    _parse_tool_input,
    _to_anthropic,
    accumulator,
    build_call_kwargs,
)
from janito.agent.usage import usage_event_from_usage  # noqa: F401

from ..events import ReasoningEvent, TokenEvent

logger = logging.getLogger(__name__)


def create_client(base_url, api_key):
    """Create the async native Anthropic SDK client, guarding the optional package."""
    if importlib.util.find_spec("anthropic") is None:
        raise RuntimeError(
            "API type 'Anthropic' requires the optional 'anthropic' package, "
            "which is not installed. Install it with: pip install anthropic"
        )
    from anthropic import AsyncAnthropic

    return AsyncAnthropic(api_key=api_key, base_url=base_url)


async def stream_turn_events(client, call_kwargs: dict, acc: AnthropicTurnAccumulator):
    """Stream one Anthropic Messages turn, yielding reasoning/token events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly (``run_tool_turn`` / ``DoneEvent``).
    """
    stream = await client.messages.create(**call_kwargs)
    async for event in stream:
        reasoning_delta, content_delta = acc.handle(event)
        if reasoning_delta:
            yield ReasoningEvent(content=reasoning_delta)
        if content_delta:
            yield TokenEvent(content=content_delta)
        if acc.done:
            break


__all__ = [
    "AnthropicTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "create_client",
    "stream_turn_events",
    "_convert_tools",
    "_parse_tool_input",
    "_to_anthropic",
    "usage_event_from_usage",
]
