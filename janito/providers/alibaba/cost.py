"""Cost estimation for the Alibaba (DashScope) provider.

Rates source
------------
The per-1M-token rates below were taken from
https://www.qwencloud.com/models/qwen3.8-max (the official QwenCloud model
marketplace, last verified 2026-08-15) and apply as of the verification
date.  Alibaba adjusts figures frequently, so cross-check the official rate
card at https://www.qwencloud.com/pricing/token-plan before relying on
them.
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)``.
#:
#: Alibaba applies automatic prefix caching: repeated input tokens (a
#: stable system prompt, a long document, few-shot examples) are billed at
#: the much lower implicit cache-hit rate instead of the cache-miss rate.
#: There is no peak-hour surcharge.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "qwen3.8-max": (2.0, 0.25, 6.0),
}


def get_cost(model: str, input: int, output: int, cached: int) -> str:
    """Estimate the monetary cost of a request in dollars.

    Args:
        model: The model name used for the request.
        input: The number of input tokens.
        output: The number of output tokens.
        cached: The number of cached input tokens.

    Returns:
        The estimated cost formatted as a dollar string with six decimal
        digits (e.g. ``"0.420000$"``), or ``"N/A"`` for an unknown model.
    """
    rates = _MODEL_RATES.get(model)
    if rates is None:
        return "N/A"
    input_miss, input_hit, output_rate = rates
    cost = (
        (input - cached) * input_miss + cached * input_hit + output * output_rate
    ) / 1_000_000
    return f"{cost:.6f}$"
