"""Cost estimation for the Z.ai (Zhipu) provider.

Rates source
------------
The per-1M-token rates below were taken from the official Z.ai pricing page
at https://docs.z.ai/guides/overview/pricing (last verified 2026-08-18) and
apply as of the verification date.  Z.ai adjusts figures frequently, so
cross-check that page before relying on them.

Prompt caching
--------------
Z.ai applies automatic context caching: cached input tokens are billed at
the much lower cache-hit rate ($0.26/1M, ~19% of the cache-miss input rate)
instead of the cache-miss rate.  Cached-input storage is billed as
"Limited-time Free" per the official pricing page, so it does not
contribute to the estimate.  There is no peak-hour surcharge.
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)``.
#:
#: Z.ai applies automatic context caching: repeated input tokens (a stable
#: system prompt, a long document, few-shot examples) are billed at the much
#: lower cache-hit rate instead of the cache-miss rate.  Cached-input
#: storage is "Limited-time Free" per the official pricing page, so it does
#: not contribute to the estimate.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "glm-5.2": (1.40, 0.26, 4.40),
}


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
        cached: The number of cached input tokens (cache hits).
        is_reference: Marks the request as a reference request (e.g. tokens
            from attached reference documents).  Passed through for future
            reference-token billing; currently the estimate is unchanged.

    Returns:
        The estimated cost formatted as a dollar string with six decimal
        digits (e.g. ``"5.800000$"``), or ``"N/A"`` for an unknown model.
    """
    rates = _MODEL_RATES.get(model)
    if rates is None:
        return "N/A"
    input_miss, input_hit, output_rate = rates
    cost = (
        (input - cached) * input_miss + cached * input_hit + output * output_rate
    ) / 1_000_000
    return f"{cost:.6f}$"
