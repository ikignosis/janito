"""Cost estimation for the DeepSeek provider."""


def get_cost(model: str, input: int, output: int, cached: int) -> str:
    """Estimate the monetary cost of a request in dollars.

    Args:
        model: The model name used for the request.
        input: The number of input tokens.
        output: The number of output tokens.
        cached: The number of cached input tokens.

    Returns:
        The estimated cost formatted as a dollar string (e.g. ``"1$"``).
    """
    return "1$"
