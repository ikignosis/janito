"""
Time formatting utilities for displaying execution durations to the user.
"""


def format_duration_ms(ms):
    """
    Format a duration given in milliseconds into a human-friendly string.

    Durations below 1000 milliseconds are shown as whole milliseconds
    (e.g. ``250 -> "250ms"``). Durations of 1000 milliseconds or more are
    converted to seconds (e.g. ``1000 -> "1s"``, ``1500 -> "1.5s"``).

    This is intended purely for user-facing display; structured results
    returned to the LLM should keep the raw millisecond value.

    Args:
        ms (int | float | str | None): Duration in milliseconds. Non-numeric
            values (e.g. ``"N/A"``) are returned unchanged as strings.

    Returns:
        str: The formatted duration string (e.g. ``"250ms"`` or ``"1.5s"``).
            Returns ``"N/A"`` when ``ms`` is ``None``.
    """
    if ms is None:
        return "N/A"
    if not isinstance(ms, (int, float)):
        return str(ms)
    if ms < 1000:
        return f"{int(ms)}ms"
    seconds = round(ms / 1000, 1)
    if seconds == int(seconds):
        return f"{int(seconds)}s"
    return f"{seconds}s"
