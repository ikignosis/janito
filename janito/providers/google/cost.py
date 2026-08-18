"""Cost estimation for the Google (Gemini) provider.

Rates source
------------
The per-1M-token rates below were taken from the official Google Gemini
rate card at https://ai.google.dev/pricing and apply as of the verification
date.  Google adjusts figures frequently, so cross-check that page before
relying on them.
"""

#: Per-1M-token rates (USD) keyed by model name:
#: ``(input cache miss, input cache hit, output)``.
#:
#: Google applies context caching: cached input tokens are billed at the
#: context cache read rate ($0.1875/1M, 25% of input token price).
#: There is no peak-hour surcharge.
_MODEL_RATES: dict[str, tuple[float, float, float]] = {
    "gemini-3.7-flash": (0.75, 0.1875, 3.75),
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
        digits (e.g. ``"4.500000$"``), or ``"N/A"`` for an unknown model.
    """
    rates = _MODEL_RATES.get(model)
    if rates is None:
        return "N/A"
    input_miss, input_hit, output_rate = rates
    cost = (
        (input - cached) * input_miss + cached * input_hit + output * output_rate
    ) / 1_000_000
    return f"{cost:.6f}$"
