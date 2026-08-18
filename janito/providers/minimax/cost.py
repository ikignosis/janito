"""Cost estimation for the MiniMax provider.

Rates source
------------
The per-1M-token rates below are based on the official MiniMax Pay-as-You-Go
Standard Tier pricing at https://platform.minimax.io/docs/guides/pricing-paygo
and apply as of the verification date.

High-context prompts
--------------------
Requests whose input exceeds 512K tokens (> 512,000 tokens) are billed at
2x the standard input rate ($0.60/1M) and 2x the standard output rate
($2.40/1M) for the whole request. Cached-input reads scale with the input
rate, so they are also billed at 2x ($0.12/1M) in high-context mode.

Prompt caching
--------------
MiniMax applies prompt cache reads: cached input tokens are billed at
$0.06/1M tokens (20% of the uncached input rate, or $0.12/1M in high-context
mode).
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)`` for standard requests.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "MiniMax-M3": (0.30, 0.06, 1.20),
    "minimax-m3": (0.30, 0.06, 1.20),
}

#: Input-token count above which the whole request is billed as high-context
#: (2x input / 2x output). Requests at or below this count use standard rates.
_HIGH_CONTEXT_INPUT_TOKENS = 512_000

#: High-context multipliers applied to the whole request: ``(input, output)``.
#: Cached-input reads scale with the input multiplier.
_HIGH_CONTEXT_MULTIPLIERS = (2.0, 2.0)


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
            from attached reference documents). Passed through for future
            reference-token billing; currently the estimate is unchanged.

    Returns:
        The estimated cost formatted as a dollar string with six decimal
        digits (e.g. ``"1.500000$"``), or ``"N/A"`` for an unknown model.
    """
    rates = _MODEL_RATES.get(model)
    if rates is None:
        return "N/A"
    input_miss, input_hit, output_rate = rates
    if input > _HIGH_CONTEXT_INPUT_TOKENS:
        input_multiplier, output_multiplier = _HIGH_CONTEXT_MULTIPLIERS
        input_miss *= input_multiplier
        input_hit *= input_multiplier
        output_rate *= output_multiplier
    cost = (
        (input - cached) * input_miss + cached * input_hit + output * output_rate
    ) / 1_000_000
    return f"{cost:.6f}$"
