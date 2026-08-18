"""Cost estimation for the xAI (Grok) provider.

Rates source
------------
The per-1M-token rates below were taken from the official xAI pricing
tables at https://docs.x.ai/developers/models (last verified 2026-08-18)
and apply as of the verification date.  xAI adjusts figures frequently,
so cross-check that page before relying on them.

Long-context prompts
--------------------
Requests whose input exceeds 200K tokens are billed at 2x the standard
rates ($4.00/1M input, $1.00/1M cached input, $12.00/1M output) for the
**whole** request -- not just the portion above the threshold.  Cached-input
reads scale with the input rate, so they are also billed at 2x ($1.00/1M)
in long-context mode.

Prompt caching
--------------
xAI applies automatic prompt caching: repeated input tokens (a stable
system prompt, a long document, few-shot examples) are billed at the much
lower cache-hit rate ($0.50/1M, 25% of the input rate) instead of the
cache-miss rate.  There is no peak-hour surcharge.
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)`` for standard requests.
#:
#: xAI applies automatic prompt caching: repeated input tokens (a stable
#: system prompt, a long document, few-shot examples) are billed at the much
#: lower cache-read rate ($0.50/1M, 25% of the input rate) instead of the
#: cache-miss rate.  There is no peak-hour surcharge.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "grok-4.6": (2.00, 0.50, 6.00),
}

#: Input-token count above which the whole request is billed as long-context
#: (2x input / 2x output).  Requests at or below this count use the
#: standard rates.
_LONG_CONTEXT_INPUT_TOKENS = 200_000

#: Long-context multipliers applied to the whole request: ``(input, output)``.
#: Cached-input reads scale with the input multiplier.
_LONG_CONTEXT_MULTIPLIERS = (2.0, 2.0)


def get_cost(
    model: str,
    input: int,
    output: int,
    cached: int,
    is_reference: bool = False,
) -> str:
    """Estimate the monetary cost of a request in dollars.

    Args:
        model: The model name used for the request.
        input: The number of input tokens.
        output: The number of output tokens.
        cached: The number of cached input tokens (cache reads).
        is_reference: Marks the request as a reference request (e.g. tokens
            from attached reference documents).  Passed through for future
            reference-token billing; currently the estimate is unchanged.

    Returns:
        The estimated cost formatted as a dollar string with six decimal
        digits (e.g. ``"2.500000$"``), or ``"N/A"`` for an unknown model.
    """
    rates = _MODEL_RATES.get(model)
    if rates is None:
        return "N/A"
    input_miss, input_hit, output_rate = rates
    if input > _LONG_CONTEXT_INPUT_TOKENS:
        input_multiplier, output_multiplier = _LONG_CONTEXT_MULTIPLIERS
        input_miss *= input_multiplier
        input_hit *= input_multiplier
        output_rate *= output_multiplier
    cost = (
        (input - cached) * input_miss + cached * input_hit + output * output_rate
    ) / 1_000_000
    return f"{cost:.6f}$"
