"""Responses API runner for the web agentic loop.

This module is the ``"Responses"`` counterpart of the Completions path in
``call.py``: it creates the OpenAI client, builds the per-turn
``client.responses.create`` kwargs, and streams the typed SSE events while
yielding reasoning/token events to the browser.

**Conversation model.** The web always uses the **stateless** Responses
input-items model: every round converts the caller-owned OpenAI-format
``messages`` history into Responses ``input`` items and re-sends the whole
conversation (system message, user/assistant turns, function_call and
function_call_output items).  This works with every ``/responses`` endpoint
-- including providers whose endpoint keeps server-side state (OpenAI), for
which re-sending the full input is equivalent, and providers whose endpoint
is stateless (DeepSeek), which *require* it.  ``session.messages`` therefore
stays in the portable OpenAI format (frontend rendering + on-disk
persistence unchanged) and never needs a server-side ``response_id``.
"""

import json
import logging

from ..events import ReasoningEvent, TokenEvent
from .call import usage_event_from_usage

logger = logging.getLogger(__name__)


def create_client(base_url, api_key):
    """Create the async OpenAI SDK client (base_url may be ``None``)."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def _convert_tools(tools_schemas: list[dict]) -> list[dict]:
    """Convert Chat Completions tool schemas to the Responses API format."""
    from janito.openai_client.responses_stream import _convert_tools_to_responses_format

    return _convert_tools_to_responses_format(tools_schemas)


def _text_of(content) -> str:
    """Coerce a message's content to the plain text the Responses API expects."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content)


def _messages_to_input_items(messages: list[dict]) -> list[dict]:
    """Convert OpenAI-format history into Responses ``input`` items.

    The web session stores the conversation in the portable OpenAI chat
    format (so the frontend and on-disk persistence are API-type agnostic).
    This maps that history onto the Responses input item shapes:

    - ``system`` / ``user`` / plain ``assistant`` messages -> ``message``
      items (``input_text`` / ``output_text`` content).
    - an ``assistant`` message with ``tool_calls`` -> one ``function_call``
      item per call (plus a ``message`` item when it also carries text).
    - ``tool`` messages -> ``function_call_output`` items.
    """
    items: list[dict] = []
    for m in messages:
        if m.get("role") == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": m.get("tool_call_id", ""),
                    "output": _text_of(m.get("content")),
                }
            )
        elif m.get("tool_calls"):
            content = m.get("content")
            if content:
                items.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": content}],
                    }
                )
            for tc in m["tool_calls"]:
                items.append(
                    {
                        "type": "function_call",
                        "call_id": tc.get("id", ""),
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                )
        else:
            role = m.get("role", "user")
            text_type = "output_text" if role == "assistant" else "input_text"
            items.append(
                {
                    "type": "message",
                    "role": role,
                    "content": [
                        {"type": text_type, "text": _text_of(m.get("content"))}
                    ],
                }
            )
    return items


def build_call_kwargs(
    model: str,
    messages: list[dict],
    tools_schemas: list[dict] | None,
    config,
    max_output_tokens: int | None,
    preserve_thinking,
    reasoning_level: str | None,
) -> dict:
    """Build the ``client.responses.create`` kwargs for one turn.

    Mirrors ``janito.openai_client.responses_state._build_call_kwargs``
    (same max_output_tokens / reasoning / preserve_thinking / thinking
    handling) but always drives the stateless input-items model, so no
    ``previous_response_id`` / ``instructions`` are ever needed: the full
    conversation is converted from ``messages`` on every round.
    """
    call_kwargs: dict = {
        "model": model,
        "input": _messages_to_input_items(messages),
        "temperature": 1.0,
        "stream": True,
    }

    if max_output_tokens is not None:
        call_kwargs["max_output_tokens"] = max_output_tokens

    if reasoning_level:
        call_kwargs["reasoning"] = {"effort": reasoning_level}

    if preserve_thinking is not None:
        call_kwargs.setdefault("extra_body", {})[
            "preserve_thinking"
        ] = preserve_thinking

    if config.effective_thinking:
        call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True

    if tools_schemas:
        call_kwargs["tools"] = _convert_tools(tools_schemas)
        call_kwargs["tool_choice"] = "auto"
    return call_kwargs


class ResponsesTurnAccumulator:
    """Fold Responses API stream events into one turn's collected state.

    Implements the same interface as :class:`~janito.web.backend.agent.call.StreamAccumulator`
    (``handle`` -> ``(reasoning_delta, content_delta)`` plus the end-of-turn
    accessors) so the orchestration loop in ``loop.py`` treats every API type
    identically.  Tool calls carry a stable ``call_id`` per finished output
    item (the Responses API does not split them across indexed chunks), and
    are exposed in the OpenAI wire format the tool-turn runner expects.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: list[dict] = []  # [{call_id, name, arguments}]
        self.partial_arguments: dict[str, str] = {}
        self.usage = None

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def handle(self, event) -> tuple[str | None, str | None]:
        """Process one stream event; returns ``(reasoning_delta, content_delta)``."""
        event_type = getattr(event, "type", None)

        # Some OpenAI-compatible providers stream API errors as untyped SSE
        # events carrying ``code``/``message``; surface them instead of
        # returning an empty answer.
        if event_type is None:
            self._raise_untyped_error(event)
            return None, None

        if event_type in ("response.created", "response.completed"):
            self.handle_completion_event(event)
        elif event_type == "response.failed":
            self._raise_failed_error(event)
        elif event_type == "response.output_text.delta":
            return None, self.handle_text_delta(event)
        elif event_type in (
            "response.reasoning_text.delta",
            "response.reasoning_summary_text.delta",
        ):
            return self.handle_text_delta(event), None
        elif event_type == "response.function_call_arguments.delta":
            self.handle_call_arguments_delta(event)
        elif event_type == "response.function_call_arguments.done":
            self.handle_call_arguments_done(event)
        elif event_type == "response.output_item.done":
            self.handle_output_item(event)
        return None, None

    def handle_completion_event(self, event) -> None:
        """Record the usage reported on the completed event."""
        response = getattr(event, "response", None)
        usage = getattr(response, "usage", None)
        if usage:
            self.usage = usage

    def handle_text_delta(self, event) -> str | None:
        """Collect one text/reasoning delta; returns the delta (or ``None``)."""
        delta = getattr(event, "delta", None)
        if not delta:
            return None
        if event.type == "response.output_text.delta":
            self.content.append(delta)
        else:
            self.reasoning.append(delta)
        return delta

    def handle_call_arguments_delta(self, event) -> None:
        """Accumulate per-item function_call arguments (split across deltas)."""
        item_id = getattr(event, "item_id", None)
        self.partial_arguments[item_id] = self.partial_arguments.get(item_id, "") + (
            getattr(event, "delta", None) or ""
        )

    def handle_call_arguments_done(self, event) -> None:
        """Record the final arguments of a finished function_call item."""
        item_id = getattr(event, "item_id", None)
        self.partial_arguments[item_id] = getattr(event, "arguments", None) or ""

    def handle_output_item(self, event) -> None:
        """Append a finished function_call output item to the tool calls."""
        item = getattr(event, "item", None)
        if getattr(item, "type", None) == "function_call":
            self.tool_calls.append(
                {
                    "call_id": getattr(item, "call_id", ""),
                    "name": getattr(item, "name", ""),
                    "arguments": getattr(item, "arguments", None)
                    or self.partial_arguments.get(getattr(item, "id", ""), ""),
                }
            )

    def _raise_untyped_error(self, event) -> None:
        """Raise for an untyped event carrying an error payload, else skip."""
        message = getattr(event, "message", None)
        code = getattr(event, "code", None)
        if message or code:
            raise RuntimeError(f"{code}: {message}" if code else message)

    def _raise_failed_error(self, event) -> None:
        """Raise the provider error carried by a ``response.failed`` event."""
        error = getattr(getattr(event, "response", None), "error", None)
        message = getattr(error, "message", None) if error else None
        raise RuntimeError(message or "Response failed")

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
                "id": tc["call_id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            }
            for tc in self.tool_calls
        ]

    def usage_event(self, max_tokens: int | None = None):
        return usage_event_from_usage(self.usage, max_tokens)


# Uniform runner interface (used by loop.py): the accumulator class is
# exposed as ``accumulator`` so every API-type runner has the same shape.
accumulator = ResponsesTurnAccumulator


async def stream_turn_events(client, call_kwargs: dict, acc: ResponsesTurnAccumulator):
    """Stream one Responses turn, yielding reasoning/token events.

    The caller owns ``acc``; on completion it holds the full turn state for
    end-of-turn assembly (``run_tool_turn`` / ``DoneEvent``).
    """
    stream = await client.responses.create(**call_kwargs)
    async for event in stream:
        reasoning_delta, content_delta = acc.handle(event)
        if reasoning_delta:
            yield ReasoningEvent(content=reasoning_delta)
        if content_delta:
            yield TokenEvent(content=content_delta)


__all__ = [
    "ResponsesTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "create_client",
    "stream_turn_events",
]
