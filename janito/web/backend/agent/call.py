"""OpenAI call-parameter building and stream accumulation.

``build_call_kwargs`` centralizes every model/provider quirk (gpt-5 token
limits, preserve_thinking, enable_thinking) that used to live inline in the
agentic loop.  ``StreamAccumulator`` folds raw streamed chunks into the
collected content / reasoning / tool-call fragments; the caller owns the
``async for`` so it can yield token events *while* the stream is arriving
(preserving live streaming — chunks must not be buffered to completion).
"""

from dataclasses import dataclass, field


def build_call_kwargs(
    model: str,
    config,
    context_window_size: int | None,
    preserve_thinking,
) -> dict:
    """Build the base ``chat.completions.create`` parameters for one turn.

    Config-driven behaviour (from CLI args):
      - ``config.thinking`` -> add extra_body enable_thinking
      - context window from ``janito.general_config`` -> max_tokens
        (``max_completion_tokens`` for gpt-5 models)
      - ``preserve_thinking`` config value -> extra_body
    """
    call_kwargs: dict = {
        "model": model,
        "temperature": 1.0,
    }

    if context_window_size is not None:
        if model.startswith("gpt-5"):
            call_kwargs["max_completion_tokens"] = context_window_size
        else:
            call_kwargs["max_tokens"] = context_window_size

    if preserve_thinking is not None:
        call_kwargs.setdefault("extra_body", {})[
            "preserve_thinking"
        ] = preserve_thinking

    if config.thinking:
        call_kwargs.setdefault("extra_body", {})["enable_thinking"] = True

    call_kwargs["stream"] = True
    call_kwargs["stream_options"] = {"include_usage": True}
    return call_kwargs


@dataclass
class StreamAccumulator:
    """Folds streamed completion chunks into one turn's collected state.

    ``handle(chunk)`` returns the reasoning/text fragment carried by the
    chunk (or ``None``) so the caller can forward it to the client
    immediately, while the accumulator retains the full picture for
    end-of-turn assembly.
    """

    content: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    tool_calls: dict[int, dict[str, str]] = field(default_factory=dict)
    usage: object | None = None

    def handle(self, chunk) -> tuple[str | None, str | None]:
        """Process one chunk; returns ``(reasoning_delta, content_delta)``."""
        if hasattr(chunk, "usage") and chunk.usage:
            self.usage = chunk.usage

        if not chunk.choices:
            return None, None

        delta = chunk.choices[0].delta

        # Reasoning / thinking content
        reasoning_delta = None
        for attr in ("reasoning_content", "reasoning"):
            val = getattr(delta, attr, None)
            if val:
                reasoning_delta = val
                self.reasoning.append(val)
                break

        # Main content
        content_delta = delta.content
        if content_delta:
            self.content.append(content_delta)

        # Tool-call deltas (split across many chunks)
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc_delta in delta.tool_calls:
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
            max_tokens: The configured context-window / max-tokens limit
                (from ``build_call_kwargs``), surfaced as ``input/max``.
        """
        if not self.usage:
            return None
        from ..events import UsageEvent

        usage = self.usage
        return UsageEvent(
            total=getattr(usage, "total_tokens", 0) or 0,
            input=getattr(usage, "prompt_tokens", 0) or 0,
            output=getattr(usage, "completion_tokens", 0) or 0,
            cached=(
                getattr(
                    getattr(usage, "prompt_tokens_details", None),
                    "cached_tokens",
                    0,
                )
                or 0
            ),
            max_tokens=max_tokens,
        )
