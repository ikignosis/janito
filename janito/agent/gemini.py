"""Shared native Gemini SDK adapter: kwargs, conversion, accumulation.

The native Gemini ``generateContent`` turn pipeline used to be CLI-only; the
pure parts -- call-kwargs building, history conversion and stream
accumulation -- live here so both agent loops share them.  The web shim
(``janito.web.backend.agent.gemini``) keeps the async glue
(:func:`create_client` and :func:`stream_turn_events`), which consumes the
**sync** ``google-genai`` stream chunk-by-chunk through ``asyncio.to_thread``.

The ``google-genai`` package is **optional** (see
``janito.providers.REQUIRES_BY_API_TYPE``); importing it happens lazily
inside :func:`create_client` (kept in the web shim), so importing this
module never requires it.

**Conversation model.** The ``generateContent`` API is stateless, so every
round re-sends the full history.  The session stores the conversation in the
portable OpenAI chat format; :func:`janito.gemini_helpers._messages_to_contents`
converts it on the fly: system messages are folded into the top-level
``system_instruction``, ``assistant`` ``tool_calls`` become ``function_call``
parts (with the model's ``thought_signature`` re-attached), and ``tool``
messages become ``function_response`` parts in a ``user`` content.  Gemini
3.x thought blocks are kept verbatim (``thought_parts``) so stateless
multi-turn requests resend them, preserving reasoning continuity.
"""

import json
import logging

from janito.gemini_helpers import _build_call_kwargs as _build_gemini_call_kwargs
from janito.gemini_helpers import _resolve_system_instruction
from janito.openai_client.gemini_stream import GeminiStreamConsumer

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
    """Build the ``generate_content_stream`` kwargs for one turn.

    Mirrors ``janito.gemini_api._build_call_kwargs``: the OpenAI-format
    history is converted to Gemini ``contents`` (with the leading
    ``system``-role message folded into ``system_instruction``) and the
    function-tool schemas to ``function_declarations``.  The resolved
    reasoning level rides in ``thinking_config.thinking_level``, which the
    Gemini API maps to the model's thinking depth.  ``preserve_thinking``
    is accepted for signature parity but is not used by the native SDK.
    """
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config
    system = _resolve_system_instruction(None, messages)
    return _build_gemini_call_kwargs(
        model,
        messages,
        max_output_tokens,
        system,
        reasoning_level,
        tools_schemas,
    )


class GeminiTurnAccumulator(GeminiStreamConsumer):
    """Fold Gemini ``generate_content_stream`` chunks (web agent loop).

    Reuses :class:`~janito.openai_client.gemini_stream.GeminiStreamConsumer`
    for the per-chunk folding (thought / text / ``function_call`` parts,
    usage metadata, ``done`` flag) and adds the web-loop accessors:
    :meth:`tool_calls_list` returns the OpenAI wire format that
    ``run_tool_turn`` expects (keeping the per-call ``thought_signature`` so
    the assistant message can echo it back), and :meth:`usage_event` maps the
    Gemini usage metadata onto a :class:`~janito.agent.events.UsageEvent`.
    """

    def tool_calls_list(self) -> list[dict]:
        """Assembled tool calls in OpenAI wire format (for ``run_tool_turn``)."""
        calls = []
        for entry in self.tool_calls.values():
            call = {
                "id": entry["id"],
                "type": "function",
                "function": {
                    "name": entry["name"],
                    "arguments": entry["arguments"]
                    or (json.dumps(entry["args"]) if entry["args"] else "{}"),
                },
            }
            if entry.get("thought_signature"):
                call["thought_signature"] = entry["thought_signature"]
            calls.append(call)
        return calls

    def usage_event(self, max_tokens: int | None = None):
        usage = self.usage_info()
        if usage is None or (
            usage.total_tokens is None
            and usage.input_tokens is None
            and usage.output_tokens is None
        ):
            return None
        return usage_event_from_usage(usage, max_tokens)


# Uniform runner interface (used by loop.py): the accumulator class is
# exposed as ``accumulator`` so every API-type runner has the same shape.
accumulator = GeminiTurnAccumulator


__all__ = [
    "GeminiTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
]
