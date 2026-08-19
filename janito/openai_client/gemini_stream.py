"""
Stream consumption for the native Gemini API (``generate_content_stream``).

These helpers are shared by the native Gemini client modules (the CLI
``janito.gemini_api`` and the web agent's shared adapter
:mod:`janito.agent.gemini`).  They assemble the streamed ``GenerateContentResponse``
chunks -- whose ``candidates[0].content.parts`` carry thought text, final
text and ``function_call`` parts -- into a single response.

The per-chunk folding lives in :class:`GeminiStreamConsumer`; the module-level
``_consume_stream`` / ``_consume_chunk`` functions are thin delegators kept for
backward compatibility with the other client modules (they are re-exported
from ``janito.gemini_api``).

Streaming chunks are ``GenerateContentResponse`` objects; each chunk exposes:

- ``candidates`` -- a list of ``Candidate`` (``content.parts`` and
  ``finish_reason``);
- ``usage_metadata`` -- the final chunk carries the turn's token counts
  (``prompt_token_count`` / ``response_token_count`` / ``total_token_count``).

Gemini 3.x streams **thought** parts alongside the answer (``part.thought``
True with the thought-summary ``text`` and an opaque ``thought_signature``).
Stateless multi-turn requests must resend those thought blocks verbatim, so
the consumer keeps them (``thought_parts``) alongside the reasoning text for
the caller to fold back into the conversation history.
"""

import json
import logging
from typing import Any

from .client_support import _extract_raw_attrs

# Configure logger for this module
logger = logging.getLogger(__name__)


class GeminiStreamConsumer:
    """Assemble Gemini ``generate_content_stream`` chunks (CLI).

    The consumer owns the accumulated content / reasoning text, the raw
    thought blocks (text + signature, resent verbatim on the next turn) and
    the per-call tool-call map keyed by function-call id.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.thought_parts: list[dict[str, Any]] = []
        self.tool_calls: dict[str, dict[str, Any]] = {}
        self.usage: Any = None
        self.raw_attrs: dict[str, Any] = {}
        self.done: bool = False

    # ------------------------------------------------------------------
    # Chunk folding
    # ------------------------------------------------------------------

    def handle(self, chunk) -> tuple[str | None, str | None]:
        """Process one chunk; returns ``(reasoning_delta, content_delta)``.

        Also captures the chunk's raw top-level metadata (``model_version``,
        ``response_id``, ``create_time``, ...) and the terminal
        ``finish_reason`` for the verbose response dump.
        """
        usage = getattr(chunk, "usage_metadata", None)
        if usage is not None:
            self.usage = usage

        self.raw_attrs.update(
            _extract_raw_attrs(chunk, skip=("candidates", "usage_metadata"))
        )

        reasoning_delta: str | None = None
        content_delta: str | None = None
        for candidate in getattr(chunk, "candidates", None) or []:
            parts = getattr(getattr(candidate, "content", None), "parts", None) or []
            for part in parts:
                delta = self._fold_part(part)
                if delta:
                    text, kind = delta
                    if kind == "reasoning":
                        reasoning_delta = text
                    elif kind == "content":
                        content_delta = text
            finish = getattr(candidate, "finish_reason", None)
            if finish is not None:
                finish_name = getattr(finish, "name", None) or str(finish)
                self.raw_attrs["finish_reason"] = finish_name
                if finish_name != "FINISH_REASON_UNSPECIFIED":
                    self.done = True
        return reasoning_delta, content_delta

    def _fold_part(self, part) -> tuple[Any, str] | None:
        """Fold one ``Part``; returns ``(text, "reasoning" | "content")`` or None."""
        # Thought blocks: reasoning text plus the signature that must be
        # resent verbatim on the next turn.
        if getattr(part, "thought", False):
            text = getattr(part, "text", None) or ""
            if text:
                self.reasoning.append(text)
                self.thought_parts.append(
                    {
                        "text": text,
                        "thought_signature": getattr(part, "thought_signature", None),
                    }
                )
                return text, "reasoning"
            return None

        function_call = getattr(part, "function_call", None)
        if function_call is not None:
            self._fold_function_call(
                function_call, getattr(part, "thought_signature", None)
            )
            return None

        text = getattr(part, "text", None)
        if text:
            self.content.append(text)
            return text, "content"
        return None

    def _fold_function_call(self, function_call, thought_signature: str | None) -> None:
        """Merge one ``FunctionCall`` part into the per-id tool-call map.

        Gemini 3 generates a unique ``id`` for every function call; the
        call's ``args`` arrive as a complete dict (streamed argument
        fragments are a Vertex-Enterprise-only feature).  The signature the
        model attached to the call part is kept so the next round can resend
        it (dropping it makes Gemini 3.x reject the follow-up request).
        """
        call_id = getattr(function_call, "id", None) or getattr(
            function_call, "name", None
        )
        key = call_id or f"call_{len(self.tool_calls)}"
        entry = self.tool_calls.setdefault(
            key,
            {
                "id": call_id or "",
                "name": getattr(function_call, "name", None) or "",
                "args": {},
                "arguments": "",
                "thought_signature": thought_signature or "",
            },
        )
        if getattr(function_call, "id", None):
            entry["id"] = function_call.id
        name = getattr(function_call, "name", None)
        if name:
            entry["name"] = name
        args = getattr(function_call, "args", None)
        if isinstance(args, dict):
            entry["args"].update(args)
        elif isinstance(args, str):
            # Rare fallback: fragment-style arguments accumulate as text.
            entry["arguments"] += args

    # ------------------------------------------------------------------
    # End-of-turn assembly
    # ------------------------------------------------------------------

    def full_content(self) -> str:
        return "".join(self.content)

    def reasoning_content(self) -> str | None:
        return "".join(self.reasoning) if self.reasoning else None

    def tool_calls_list(self) -> list[dict[str, Any]]:
        """Assembled tool calls in the CLI wire format.

        Each entry carries ``id`` / ``name`` / ``arguments`` (JSON string)
        plus the model's ``thought_signature`` when one was attached, so the
        caller can echo it back on the next round.
        """
        calls = []
        for entry in self.tool_calls.values():
            call: dict[str, Any] = {
                "id": entry["id"],
                "name": entry["name"],
                "arguments": entry["arguments"]
                or (json.dumps(entry["args"]) if entry["args"] else "{}"),
            }
            if entry.get("thought_signature"):
                call["thought_signature"] = entry["thought_signature"]
            calls.append(call)
        return calls

    def usage_info(self):
        """Map the last ``usage_metadata`` onto the shared usage shape."""
        from janito.gemini_helpers import _build_usage_info

        return _build_usage_info(self.usage)

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def consume(self, stream, cancel_event=None):
        """Consume a Gemini stream and assemble the response parts.

        Returns ``(full_content, reasoning_content, tool_calls_list,
        usage_info, raw_attrs, thought_parts)`` where ``thought_parts`` holds
        the raw thought blocks (text + signature) to resend verbatim on the
        next turn.

        When ``cancel_event`` is set (user pressed Enter while waiting), the
        stream is abandoned as soon as the next chunk arrives.

        Raises:
            RuntimeError: If the stream yields no chunks at all (never an
                empty answer).
        """
        consumed = False
        for chunk in stream:
            consumed = True
            if cancel_event is not None and cancel_event.is_set():
                break
            self.handle(chunk)
        if not consumed:
            raise RuntimeError("Gemini API returned no stream chunks")
        return (
            self.full_content(),
            self.reasoning_content(),
            self.tool_calls_list(),
            self.usage_info(),
            self.raw_attrs,
            self.thought_parts,
        )


# ---------------------------------------------------------------------------
# Module-level delegators (re-exported from ``janito.gemini_api``).
# ---------------------------------------------------------------------------


def _consume_stream(stream, cancel_event=None):
    """Consume a Gemini stream and assemble the response parts.

    Returns ``(full_content, reasoning_content, tool_calls_list, usage_info,
    raw_attrs, thought_parts)``.  See :meth:`GeminiStreamConsumer.consume`.
    """
    return GeminiStreamConsumer().consume(stream, cancel_event=cancel_event)


def _consume_chunk(chunk, consumer: GeminiStreamConsumer | None = None):
    """Fold one Gemini stream chunk into a consumer (legacy bridge)."""
    consumer = consumer or GeminiStreamConsumer()
    consumer.handle(chunk)
    return consumer


def _stream_response(client, call_kwargs, tools_schemas, cancel_event=None):
    """Open a ``generate_content_stream`` and fully consume it.

    Returns ``(full_content, reasoning_content, tool_calls_list, usage_info,
    raw_attrs, thought_parts)``.

    When ``cancel_event`` is set (user pressed Enter while waiting), the
    stream is abandoned as soon as the next chunk arrives.
    """
    if tools_schemas:
        logger.debug(f"Calling Gemini API (streaming) with {len(tools_schemas)} tools")
    else:
        logger.debug("Calling Gemini API (streaming) without tools")
    stream = client.models.generate_content_stream(**call_kwargs)
    try:
        return _consume_stream(stream, cancel_event=cancel_event)
    finally:
        # Abort the underlying HTTP stream when the user pressed Enter so the
        # connection is released promptly instead of streaming to completion.
        if cancel_event is not None and cancel_event.is_set():
            close = getattr(stream, "close", None)
            if callable(close):
                close()
