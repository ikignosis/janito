"""Shared token-usage normalization for the CLI and web agent loops.

Both loops report token usage at the end of a turn, but each API backend
names the counters differently: Chat Completions reports
``prompt_tokens``/``completion_tokens`` (with ``prompt_tokens_details``),
the Responses API reports ``input_tokens``/``output_tokens`` (with
``input_tokens_details``), and the native SDKs (Anthropic / DashScope) build
a ``SimpleNamespace`` with ``input_tokens``/``output_tokens`` and no
cached-token details.  :func:`normalize_usage` maps every shape onto one
dict; the CLI formats it as a Rich summary line
(``janito.openai_client.client_support._display_usage``) and the web loop
serializes it as a ``UsageEvent``.
"""

from typing import Any


def normalize_usage(usage: Any) -> dict[str, Any] | None:
    """Normalize any API usage object into ``{total, input, output, cached}``.

    ``None`` values are preserved (they mean "not reported") so callers can
    decide how to display each counter.  Returns ``None`` when ``usage``
    itself is ``None``.
    """
    if usage is None:
        return None
    details = getattr(usage, "prompt_tokens_details", None) or getattr(
        usage, "input_tokens_details", None
    )
    input_tokens = getattr(usage, "prompt_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(usage, "output_tokens", None)
    return {
        "total": getattr(usage, "total_tokens", None),
        "input": input_tokens,
        "output": output_tokens,
        "cached": getattr(details, "cached_tokens", None) if details else None,
    }


def format_tokens(count):
    """Convert a token count to a human-readable format.

    Examples:
        2000 -> "2k"
        4000000 -> "4m"
        150 -> "150"
        12345 -> "12.3k"
    """
    if count is None:
        return None
    try:
        value = float(count)
    except (TypeError, ValueError):
        return count

    def _format(number):
        # Trim trailing ".0" for whole numbers (e.g. "2.0k" -> "2k")
        if number == int(number):
            return str(int(number))
        return f"{number:.1f}"

    if value >= 1_000_000:
        return f"{_format(value / 1_000_000)}m"
    if value >= 1_000:
        return f"{_format(value / 1_000)}k"
    return str(int(value))


def usage_event_from_usage(usage: Any, max_tokens: int | None = None):
    """Build a :class:`~janito.agent.events.UsageEvent` from a usage object.

    Handles every usage shape the supported API types report (see
    :func:`normalize_usage`).  Returns ``None`` when no usage was reported
    by the stream.
    """
    if usage is None:
        return None
    from .events import UsageEvent

    stats = normalize_usage(usage)
    return UsageEvent(
        total=stats["total"] or 0,
        input=stats["input"] or 0,
        output=stats["output"] or 0,
        cached=stats["cached"] or 0,
        max_tokens=max_tokens,
    )
