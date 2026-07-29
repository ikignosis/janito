"""Track which files were touched by tool calls during a session.

Whenever a tool is invoked whose *first* argument is named ``filepath``, the
value of that argument is recorded together with the name of the tool that
used it. The mapping is kept in memory for the lifetime of the process and can
be rendered as a ``Used Files`` report that is printed before the token-usage
summary.

Example of the tracked structure::

    {"/etc/hosts": ["ReadFile"]}

Like :mod:`janito.tooling.tools_usage`, the functions here are deliberately
defensive: tracking is a best-effort side feature and must never be able to
break tool execution or the agent loop, so every access is wrapped and
failures are swallowed.
"""

from __future__ import annotations

import logging
import threading

from rich.text import Text

logger = logging.getLogger(__name__)

# Name of the argument that, when it is the *first* argument of a tool call,
# marks the call as operating on a file path worth tracking.
TRACKED_ARG_NAME = "filepath"

# Serialises access from the multiple threads the web backend uses to run
# tools concurrently.
_lock = threading.Lock()

# path -> ordered list of tool names that used it (one entry per use).
_used_files: dict[str, list[str]] = {}


def record_used_file(tool_name: str, tool_args: dict) -> None:
    """Record a file path used by a tool call, if applicable.

    The call is only tracked when ``tool_args`` is a non-empty mapping whose
    first key is :data:`TRACKED_ARG_NAME` (``"filepath"``) and whose value is a
    non-empty string. This function never raises.

    Args:
        tool_name: The name of the tool that was invoked.
        tool_args: The arguments the tool was called with (insertion ordered).
    """
    try:
        if not tool_name or not isinstance(tool_args, dict) or not tool_args:
            return

        # The "first argument" is the first key of the (ordered) arguments.
        first_arg = next(iter(tool_args))
        if first_arg != TRACKED_ARG_NAME:
            return

        path = tool_args[first_arg]
        if not isinstance(path, str) or not path:
            return

        with _lock:
            _used_files.setdefault(path, []).append(tool_name)
    except Exception as e:  # noqa: BLE001 - tracking must never break execution
        logger.debug(f"Failed to record used file for '{tool_name}': {e}")


def get_used_files() -> dict[str, list[str]]:
    """Return a copy of the tracked ``path -> [tool names]`` mapping.

    Returns:
        dict[str, list[str]]: A snapshot of the used files, in insertion order.
    """
    with _lock:
        return {path: list(tools) for path, tools in _used_files.items()}


def reset_used_files() -> None:
    """Clear all tracked used files (e.g. on conversation restart)."""
    with _lock:
        _used_files.clear()


def format_used_files() -> Text:
    """Render the tracked used files as a printable ``Used Files`` report.

    The report is preceded by a blank line (to visually separate it from the
    answer) and a ``====`` header. The header line is rendered in cyan via
    :class:`rich.text.Text`. The format is::

        <blank line>
        ==== Used Files ====
        file1 ReadFile,WriteFile
        file2 ReadFile

    When nothing has been tracked, an empty :class:`~rich.text.Text` is
    returned so that no header (or ``(none)`` line) is printed at all.

    Returns:
        rich.text.Text: The multi-line report with the header styled cyan, or
        an empty ``Text`` when no files were tracked.
    """
    used = get_used_files()
    if not used:
        return Text()

    text = Text()
    # Only the header line is styled (cyan); the file paths stay default.
    text.append("\n===== Used Files =====", style="cyan")
    for path, tools in used.items():
        text.append(f"\n{path} {','.join(tools)}")
    return text


__all__ = [
    "TRACKED_ARG_NAME",
    "record_used_file",
    "get_used_files",
    "reset_used_files",
    "format_used_files",
]
