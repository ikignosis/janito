"""Completions adapter for the web agentic loop — shared with the CLI loop.

The call-parameter building and stream accumulation now live in
:mod:`janito.agent.completions` (the shared per-API adapter layer used by
both the CLI ``Client.send`` and the web ``stream_prompt`` loops).  This
module re-exports them under their historical web names so the orchestration
loop (``loop.py``) and existing tests keep their import paths.
"""

from janito.agent.completions import (  # noqa: F401
    CompletionsAccumulator,
    build_call_kwargs,
)
from janito.agent.usage import usage_event_from_usage  # noqa: F401

#: Historical web name for the shared Completions accumulator.
StreamAccumulator = CompletionsAccumulator

__all__ = [
    "CompletionsAccumulator",
    "StreamAccumulator",
    "build_call_kwargs",
    "usage_event_from_usage",
]
