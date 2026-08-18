"""Shared Responses API adapter: call kwargs, history conversion, accumulation.

The Responses-API turn pipeline used to live in the web runner
(``janito.web.backend.agent.responses``); the pure parts — call-kwargs
building, conversation-history conversion and stream accumulation — moved
here so both agent loops share them.  The web shim keeps the async glue
(:func:`create_client` and :func:`stream_turn_events`), which is loop- and
transport-specific.

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

import base64
import json
import logging
import tempfile

from janito.provider_accessors import apply_thinking_to_extra_body

from .usage import usage_event_from_usage

logger = logging.getLogger(__name__)


def _convert_tools(tools_schemas: list[dict]) -> list[dict]:
    """Convert Chat Completions tool schemas to the Responses API format."""
    from janito.openai_client.responses_stream import _convert_tools_to_responses_format

    return _convert_tools_to_responses_format(tools_schemas)


def _model_supports_image_generation(model: str) -> bool:
    """Whether a mainline Responses model supports the ``image_generation`` tool.

    Per the OpenAI image-generation guide, ``gpt-5`` and newer mainline
    models should support the built-in ``image_generation`` tool; the tool
    handles GPT Image model selection internally.  Older / third-party
    models (e.g. ``gpt-4``, DeepSeek) do not, so the tool is only appended
    for the gpt-5 family.
    """
    return bool(model) and (model == "gpt-5" or model.startswith("gpt-5."))


def _save_base64_image(b64_data: str) -> str | None:
    """Decode a base64 PNG and write it to a kept temp file.

    The file is written (not deleted) into the system temp directory so the
    ``/api/images/<filename>`` endpoint can serve it to the frontend --
    the same directory the ``CreateImage`` tool uses.  Returns the temp
    path, or ``None`` when the data cannot be decoded or written.
    """
    try:
        image_bytes = base64.b64decode(b64_data)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to decode base64 image data: {e}")
        return None
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".png", prefix="janito_image_", delete=False
        )
        tmp_path = tmp.name
        with open(tmp_path, "wb") as fh:
            fh.write(image_bytes)
        return tmp_path
    except OSError as e:
        logger.warning(f"Failed to write generated image to temp file: {e}")
        return None


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

    # Pass the thinking mode in extra_body: enable_thinking for flag-style
    # defaults, or the raw dict for providers with a structured thinking
    # parameter (e.g. MiniMax-M3's {"type": "adaptive"}).  Gemini-flavored
    # providers (google) skip enable_thinking -- the field does not exist on
    # their OpenAI-compatibility API.
    provider = getattr(config, "effective_provider", None)
    apply_thinking_to_extra_body(
        call_kwargs, config.effective_thinking, provider=provider
    )

    # Native model capabilities enabled through the Responses ``tools`` array:
    #
    # - ``image_generation``: mainline models (gpt-5+) can generate images
    #   through the Responses API's built-in ``image_generation`` tool;
    # - the effective model's built-in tools (e.g. Alibaba/Qwen's
    #   code_interpreter / web_search / web_extractor) are native
    #   capabilities whose ``{"type": ...}`` shape is already the Responses
    #   format.
    #
    # Both are model capabilities, not permissioned function tools, so they
    # are enabled whenever the model supports/declares them -- even with
    # ``no_tools`` / an empty function-tools list.  They are appended after
    # any converted function tools; neither goes through the function-schema
    # conversion.
    builtin_tools = list(config.effective_tools_for("Responses") or [])
    if builtin_tools or _model_supports_image_generation(model):
        converted_tools = _convert_tools(tools_schemas or [])
        if _model_supports_image_generation(model):
            converted_tools.append({"type": "image_generation"})
        converted_tools.extend(builtin_tools)
        call_kwargs["tools"] = converted_tools
        call_kwargs["tool_choice"] = "auto"
    elif tools_schemas:
        call_kwargs["tools"] = _convert_tools(tools_schemas)
        call_kwargs["tool_choice"] = "auto"
    return call_kwargs


class ResponsesTurnAccumulator:
    """Fold Responses API stream events into one turn's collected state.

    Implements the same interface as
    :class:`~janito.agent.completions.CompletionsAccumulator` (``handle`` ->
    ``(reasoning_delta, content_delta)`` plus the end-of-turn accessors) so
    the orchestration loop treats every API type identically.  Tool calls
    carry a stable ``call_id`` per finished output item (the Responses API
    does not split them across indexed chunks), and are exposed in the
    OpenAI wire format the tool-turn runner expects.
    """

    def __init__(self) -> None:
        self.content: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: list[dict] = []  # [{call_id, name, arguments}]
        self.partial_arguments: dict[str, str] = {}
        self.usage = None
        # Native image generation results: [{path, revised_prompt}].  The
        # built-in ``image_generation`` tool returns base64 images directly
        # in the stream; the accumulator saves each to a temp PNG file.
        self.image_results: list[dict] = []

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
        """Append a finished output item to the collected turn state.

        Handles ``function_call`` items (tool calls for the tool-turn
        runner) and ``image_generation_call`` items (native Responses-API
        image generation, saved to a temp PNG file for the frontend).
        """
        item = getattr(event, "item", None)
        item_type = getattr(item, "type", None)
        if item_type == "function_call":
            self.tool_calls.append(
                {
                    "call_id": getattr(item, "call_id", ""),
                    "name": getattr(item, "name", ""),
                    "arguments": getattr(item, "arguments", None)
                    or self.partial_arguments.get(getattr(item, "id", ""), ""),
                }
            )
        elif item_type == "image_generation_call":
            self._capture_image_generation(item)

    def _capture_image_generation(self, item) -> None:
        """Decode and save one ``image_generation_call`` result.

        The item's ``result`` is a base64-encoded image (a plain string, or
        a dict carrying ``b64_json``).  The decoded PNG is written to a
        kept temp file so the ``/api/images/`` router can serve it.
        """
        result = getattr(item, "result", None)
        b64_data = None
        if isinstance(result, str):
            b64_data = result
        elif isinstance(result, dict):
            b64_data = result.get("b64_json")
        if not b64_data:
            return
        path = _save_base64_image(b64_data)
        if path:
            self.image_results.append(
                {
                    "path": path,
                    "revised_prompt": getattr(item, "revised_prompt", None) or "",
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


__all__ = [
    "ResponsesTurnAccumulator",
    "accumulator",
    "build_call_kwargs",
    "_convert_tools",
    "_messages_to_input_items",
    "_model_supports_image_generation",
    "_save_base64_image",
    "_text_of",
]
