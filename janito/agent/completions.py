"""Shared Chat Completions adapter: call-kwargs building + stream accumulation.

Used by both agent loops:

- the web ``stream_prompt()`` loop imports ``CompletionsAccumulator`` and
  ``build_call_kwargs`` through the ``janito.web.backend.agent.call`` shim
  (where the accumulator is still aliased as ``StreamAccumulator``);
- the CLI loop subclasses ``CompletionsAccumulator`` in
  ``janito.openai_client.completions_stream`` (``CompletionsStreamConsumer``)
  to add its synchronous Enter-to-cancel stream driver.

The per-chunk folding is identical in both; only the stream *driver* differs
(web: ``async for`` yielding token events live; CLI: a sync ``consume``
loop under a progress spinner).
"""

from dataclasses import dataclass, field

from .usage import usage_event_from_usage


def build_call_kwargs(
    model: str,
    config,
    max_output_tokens: int | None,
    preserve_thinking,
    reasoning_level: str | None = None,
) -> dict:
    """Build the base ``chat.completions.create`` parameters for one turn.

    Config-driven behaviour (from CLI args):
      - ``config.effective_thinking`` (runtime toggle, else the ``--thinking``
        flag, else the provider's built-in ``thinking``) -> add
        extra_body enable_thinking
      - max output tokens from ``janito.general_config`` -> max_tokens
        (``max_completion_tokens`` for gpt-5 models)
      - ``preserve_thinking`` config value -> extra_body
      - ``reasoning_level`` -> ``reasoning_effort`` (e.g. low/medium/xhigh)

    Note: the CLI loop keeps its own ``_build_call_kwargs`` (in
    ``janito.openai_client.completions_api``) because it threads the
    ``messages`` list and a raw ``thinking`` flag through the shared
    ``Client`` template method instead of a ``WebServerConfig``.
    """
    call_kwargs: dict = {
        "model": model,
        "temperature": 1.0,
    }

    if max_output_tokens is not None:
        if model.startswith("gpt-5"):
            call_kwargs["max_completion_tokens"] = max_output_tokens
        else:
            call_kwargs["max_tokens"] = max_output_tokens

    if reasoning_level:
        call_kwargs["reasoning_effort"] = reasoning_level

    if preserve_thinking is not None:
        call_kwargs.setdefault("extra_body", {})[
            "preserve_thinking"
        ] = preserve_thinking

    thinking = config.effective_thinking
    if thinking:
        call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True

    call_kwargs["stream"] = True
    call_kwargs["stream_options"] = {"include_usage": True}
    return call_kwargs


def _raise_chunk_error(chunk) -> None:
    """Raise when a stream chunk carries an API error the SDK could not type.

    Some OpenAI-compatible providers reject a request *in-band*: instead of
    an HTTP error status they stream a single ``ChatCompletionChunk`` with no
    ``choices`` that carries the failure as ``code``/``message`` fields (e.g.
    Alibaba DashScope returns ``code='Not Found', message='Not support'``
    when a model is sent to the wrong gateway).  The OpenAI SDK cannot type
    these, so without this guard the turn would silently produce an empty
    response.  Mirrors ``responses_stream._handle_untyped_error``.
    """
    code = getattr(chunk, "code", None)
    message = getattr(chunk, "message", None)
    if code or message:
        raise RuntimeError(f"{code}: {message}" if code else message)


@dataclass
class CompletionsAccumulator:
    """Fold streamed completion chunks into one turn's collected state.

    ``handle(chunk)`` returns the reasoning/text fragment carried by the
    chunk (or ``None``) so the caller can forward it to the client
    immediately, while the accumulator retains the full picture for
    end-of-turn assembly.

    The CLI stream consumer subclasses this class to add its synchronous
    ``consume`` driver and property-style accessors; the web loop uses the
    class directly.
    """

    content: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    tool_calls: dict[int, dict[str, str]] = field(default_factory=dict)
    usage: object | None = None

    def _handle_reasoning_delta(self, delta) -> str | None:
        """Capture reasoning/thinking content; returns the delta or None."""
        for attr in ("reasoning_content", "reasoning"):
            val = getattr(delta, attr, None)
            if val:
                self.reasoning.append(val)
                return val
        return None

    def _fold_tool_call_delta(self, tc_delta) -> None:
        """Merge one tool-call delta into the per-index tool call map."""
        idx = tc_delta.index
        if idx not in self.tool_calls:
            self.tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
        if tc_delta.id:
            self.tool_calls[idx]["id"] = tc_delta.id
        if tc_delta.function:
            if tc_delta.function.name:
                self.tool_calls[idx]["name"] = tc_delta.function.name
            if tc_delta.function.arguments:
                self.tool_calls[idx]["arguments"] += tc_delta.function.arguments

    def _handle_tool_call_delta(self, delta) -> None:
        """Accumulate tool-call deltas (split across many chunks)."""
        if not hasattr(delta, "tool_calls") or not delta.tool_calls:
            return
        for tc_delta in delta.tool_calls:
            self._fold_tool_call_delta(tc_delta)

    def handle(self, chunk) -> tuple[str | None, str | None]:
        """Process one chunk; returns ``(reasoning_delta, content_delta)``."""
        if hasattr(chunk, "usage") and chunk.usage:
            self.usage = chunk.usage

        if not chunk.choices:
            _raise_chunk_error(chunk)
            return None, None

        delta = chunk.choices[0].delta

        # Reasoning / thinking content
        reasoning_delta = self._handle_reasoning_delta(delta)

        # Main content
        content_delta = delta.content
        if content_delta:
            self.content.append(content_delta)

        # Tool-call deltas (split across many chunks)
        self._handle_tool_call_delta(delta)

        return reasoning_delta, content_delta

    # --- End-of-turn assembly -------------------------------------------

    def full_content(self) -> str:
        return "".join(self.content)

    def reasoning_content(self) -> str | None:
        return "".join(self.reasoning) if self.reasoning else None

    def tool_calls_list(self) -> list[dict]:
        """Assembled tool calls in original index order (OpenAI wire format)."""
        return [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
            for tc in (self.tool_calls[i] for i in sorted(self.tool_calls))
        ]

    def usage_event(self, max_tokens: int | None = None):
        """Build a UsageEvent from the streamed usage info (or ``None``).

        Args:
            max_tokens: The configured max-output-tokens limit (from
                ``build_call_kwargs``), surfaced as ``input/max``.
        """
        return usage_event_from_usage(self.usage, max_tokens)

    @property
    def usage_info(self) -> object | None:
        """Alias of ``usage`` (the CLI stream consumer's historical name)."""
        return self.usage
