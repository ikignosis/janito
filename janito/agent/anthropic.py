"""Shared native Anthropic SDK adapter: kwargs, conversion, accumulation.

The Anthropic Messages-API turn pipeline used to live in the web runner
(``janito.web.backend.agent.anthropic``); the pure parts — call-kwargs
building, history conversion and stream accumulation — moved here so both
agent loops share them.  The web shim keeps the async glue
(:func:`create_client` and :func:`stream_turn_events`).

The ``anthropic`` package is **optional** (see
``janito.provider_data.REQUIRES_BY_API_TYPE``); importing it happens lazily
inside :func:`create_client` (kept in the web shim), so importing this
module never requires it.

**Conversation model.** The Messages API is stateless, so every round
re-sends the full history.  The session stores the conversation in the
portable OpenAI chat format; :func:`_to_anthropic` converts it on the fly:
system messages are folded into the top-level ``system`` parameter,
``assistant`` ``tool_calls`` become ``tool_use`` content blocks, and ``tool``
messages become ``tool_result`` blocks in a ``user`` message (consecutive
tool results are merged into one message so roles keep alternating).
"""

import json
import logging
from types import SimpleNamespace

from .usage import usage_event_from_usage

logger = logging.getLogger(__name__)


def _convert_tools(tools_schemas: list[dict]) -> list[dict]:
    """Convert Chat Completions tool schemas to the Anthropic tools format."""
    from janito.openai_client.anthropic_stream import _convert_tools_to_anthropic_format

    return _convert_tools_to_anthropic_format(tools_schemas)


def _parse_tool_input(arguments: str) -> dict:
    """Parse an OpenAI-format tool-call arguments string into a dict."""
    try:
        return json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {}


def _to_anthropic(messages: list[dict]) -> tuple[list[dict], str | None]:
    """Convert OpenAI-format history into ``(anthropic_messages, system)``.

    ``system``-role messages are extracted into the top-level ``system``
    parameter (a ``\\n\\n``-joined string, matching the CLI client); the
    remaining messages map onto the Messages API shapes, with assistant
    ``tool_calls`` -> ``tool_use`` content blocks and ``tool`` messages ->
    ``tool_result`` blocks inside a ``user`` message.  Consecutive ``tool``
    messages (one per tool call in a turn) are merged into a single ``user``
    message so the user/assistant roles keep alternating as the API requires.
    """
    system_parts = [
        str(m["content"])
        for m in messages
        if m.get("role") == "system" and m.get("content")
    ]
    system = "\n\n".join(system_parts) if system_parts else None

    converted: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue
        if role == "assistant" and m.get("tool_calls"):
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc["function"]["name"],
                        "input": _parse_tool_input(tc["function"]["arguments"]),
                    }
                )
            converted.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            result_block = {
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id", ""),
                "content": m.get("content") or "",
            }
            last = converted[-1] if converted else None
            if (
                last
                and last["role"] == "user"
                and isinstance(last["content"], list)
                and last["content"]
                and all(b.get("type") == "tool_result" for b in last["content"])
            ):
                last["content"].append(result_block)
            else:
                converted.append({"role": "user", "content": [result_block]})
        else:
            converted.append({"role": role, "content": m.get("content") or ""})
    return converted, system


def build_call_kwargs(
    model: str,
    messages: list[dict],
    tools_schemas: list[dict] | None,
    config,
    max_output_tokens: int | None,
    preserve_thinking,
    reasoning_level: str | None,
) -> dict:
    """Build the ``client.messages.create`` kwargs for one turn.

    The Messages API requires ``max_tokens``, so a resolved value always
    lands in the payload (config > provider built-in default > 100k, same as
    the CLI client).  ``preserve_thinking`` / ``reasoning_level`` / thinking
    are accepted for signature parity with the other runners but the native
    extended-thinking mode is not wired yet (thinking text is still streamed
    and displayed when the model emits it).
    """
    anthropic_messages, system = _to_anthropic(messages)
    if max_output_tokens is None:
        max_output_tokens = 100000  # default to 100k tokens if not set in config

    call_kwargs: dict = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": max_output_tokens,
        "stream": True,
    }
    if system:
        call_kwargs["system"] = system
    if tools_schemas:
        call_kwargs["tools"] = _convert_tools(tools_schemas)
    return call_kwargs


class AnthropicTurnAccumulator:
    """Fold Anthropic Messages stream events into one turn's collected state.

    Implements the same interface as
    :class:`~janito.agent.completions.CompletionsAccumulator` (``handle`` ->
    ``(reasoning_delta, content_delta)`` plus the end-of-turn accessors).
    Text deltas are forwarded to the browser as they arrive; ``tool_use``
    blocks are assembled per index (the ``input_json_delta`` fragments
    arrive split across events) and exposed in the OpenAI wire format the
    tool-turn runner expects.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_use_blocks: list[dict] = []  # [{id, name, input}]
        # index -> {type, id, name, json} while a tool_use block is in flight
        self.blocks: dict[int, dict] = {}
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.done: bool = False

    # ------------------------------------------------------------------
    # Stream driving
    # ------------------------------------------------------------------

    def handle(self, event) -> tuple[str | None, str | None]:
        """Process one stream event; returns ``(reasoning_delta, content_delta)``."""
        event_type = getattr(event, "type", None)

        if event_type == "message_start":
            self.handle_message_start(event)
        elif event_type == "content_block_start":
            self.handle_content_block_start(event)
        elif event_type == "content_block_delta":
            return self.handle_content_block_delta(event)
        elif event_type == "content_block_stop":
            self.handle_content_block_stop(event)
        elif event_type == "message_delta":
            self.handle_message_delta(event)
        elif event_type == "message_stop":
            self.done = True
        elif event_type == "error":
            self._raise_error(event)
        return None, None

    def handle_message_start(self, event) -> None:
        """Record the input tokens reported by the message_start event."""
        message = getattr(event, "message", None)
        usage = getattr(message, "usage", None)
        if usage is not None:
            self.input_tokens = getattr(usage, "input_tokens", None)

    def handle_content_block_start(self, event) -> None:
        """Open a new content block indexed by ``index``."""
        index = getattr(event, "index", None)
        if index is None:
            return
        block = getattr(event, "content_block", None)
        self.blocks[index] = {
            "type": getattr(block, "type", None),
            "text": "",
            "id": getattr(block, "id", None),
            "name": getattr(block, "name", None),
            "json": "",
        }

    def handle_content_block_delta(self, event) -> tuple[str | None, str | None]:
        """Accumulate a text/thinking/JSON delta; returns streamed deltas."""
        block = self.blocks.get(getattr(event, "index", None))
        delta = getattr(event, "delta", None)
        if block is None or delta is None:
            return None, None
        delta_type = getattr(delta, "type", None)
        if delta_type == "text_delta":
            text = getattr(delta, "text", "") or ""
            block["text"] += text
            if text:
                self.content.append(text)
                return None, text
        elif delta_type == "thinking_delta":
            text = getattr(delta, "thinking", "") or ""
            block["text"] += text
            if text:
                self.reasoning.append(text)
                return text, None
        elif delta_type == "input_json_delta":
            block["json"] += getattr(delta, "partial_json", "") or ""
        return None, None

    def handle_content_block_stop(self, event) -> None:
        """Flush a finished tool_use block into the collected tool calls."""
        block = self.blocks.pop(getattr(event, "index", None), None)
        if block is not None and block["type"] == "tool_use":
            self.tool_use_blocks.append(self._parse_tool_use(block))

    def handle_message_delta(self, event) -> None:
        """Record the output tokens reported by the message_delta event."""
        usage = getattr(event, "usage", None)
        if usage is not None:
            self.output_tokens = getattr(usage, "output_tokens", None)

    def _raise_error(self, event) -> None:
        """Raise the error message carried by an error event."""
        error = getattr(event, "error", None)
        if isinstance(error, dict):
            message = error.get("message")
        else:
            message = getattr(error, "message", None)
        raise RuntimeError(message or "Anthropic API error")

    def _parse_tool_use(self, block: dict) -> dict:
        """Parse a finished tool_use block into ``{"id", "name", "input"}``."""
        try:
            parsed = json.loads(block["json"]) if block["json"].strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        return {"id": block["id"], "name": block["name"], "input": parsed}

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
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block["input"]),
                },
            }
            for block in self.tool_use_blocks
        ]

    def usage_event(self, max_tokens: int | None = None):
        if self.input_tokens is None and self.output_tokens is None:
            return None
        usage = SimpleNamespace(
            total_tokens=(self.input_tokens or 0) + (self.output_tokens or 0),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )
        return usage_event_from_usage(usage, max_tokens)


# Uniform runner interface (used by loop.py): the accumulator class is
# exposed as ``accumulator`` so every API-type runner has the same shape.
accumulator = AnthropicTurnAccumulator


__all__ = [
    "AnthropicTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "_convert_tools",
    "_parse_tool_input",
    "_to_anthropic",
]
