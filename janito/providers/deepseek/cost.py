"""Cost estimation for the DeepSeek provider.

Rates source
------------
The per-1M-token rates below were taken from
https://deepseek.ai/pricing (an independent editorial site, last verified
2026-07-25, not affiliated with DeepSeek) and apply as of the verification
date.  DeepSeek adjusts figures frequently, so cross-check the official
rate card at https://api-docs.deepseek.com/quick_start/pricing before
relying on them.
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)``.
#:
#: DeepSeek applies automatic prefix caching: repeated input tokens (a
#: stable system prompt, a long document, few-shot examples) are billed at
#: the much lower cache-hit rate instead of the cache-miss rate.  There is
#: no peak-hour surcharge.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "deepseek-v4-flash": (0.14, 0.0028, 0.28),
    "deepseek-v4-pro": (0.435, 0.003625, 0.87),
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
