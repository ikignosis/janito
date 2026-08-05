#!/usr/bin/env python3
"""
Standalone Progress Reporter - For use outside of BaseTool classes.

This module provides progress reporting functions that can be used
by any code that needs to report progress to the user, including MCP tools.

In web mode, a context-variable-based report handler intercepts all report
calls and forwards them as structured events instead of printing to stderr.
"""

import difflib
from collections.abc import Callable
from contextvars import ContextVar

from rich.console import Console

# Shared console for stderr output (no auto-highlighting or markup interpretation)
_console = Console(stderr=True, highlight=False, markup=False)


# --- Pluggable report handler via contextvars ---

# A report handler receives (level, message, end).
# level is one of: "start", "progress", "output", "diff", "result", "error", "warning", "info"
ReportHandler = Callable[[str, str, str], None]

_report_handler: ContextVar[ReportHandler | None] = ContextVar(
    "_report_handler", default=None
)


def set_report_handler(handler: ReportHandler | None) -> None:
    """Set a custom report handler for the current async context.
    Pass None to restore default Rich console output."""
    _report_handler.set(handler)


def get_report_handler() -> ReportHandler | None:
    """Get the current report handler (or None for default console output)."""
    return _report_handler.get()


# Rich style names (replaces raw ANSI escape codes)
class Colors:
    CYAN = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    WHITE = "white"
    RESET = ""


def report_start(
    message: str,
    end: str = "\n",
    color: str = Colors.CYAN,
    prefix: str = " \U0001f504 ",
) -> None:
    """
    Report that an operation is starting.

    Args:
        message: The message to display
        end: String appended after the message (default: "\n")
        color: The rich style to use (default: CYAN)
        prefix: Prefix string before message (default: " 🔄 ").
                BaseTool passes prefix=" " to preserve its existing format.
    """
    handler = _report_handler.get()
    if handler:
        handler("start", message, end)
        return
    _console.print(f"{prefix}{message}", style=color, end=end)
    _console.file.flush()


def report_progress(message: str, end: str = "\n") -> None:
    """
    Report ongoing progress of an operation.

    Args:
        message: The progress message to display
        end: String appended after the message (default: "\n")
    """
    handler = _report_handler.get()
    if handler:
        handler("progress", message, end)
        return
    _console.print(f"{message}", end=end)
    _console.file.flush()


def report_output(message: str, end: str = "\n") -> None:
    """Report raw command/subprocess output (stdout/stderr lines).

    Displayed differently from progress messages:
    - CLI: printed as-is (monospace, no emoji prefix)
    - Web: rendered in a terminal-style monospace block in the ToolMonitor
    """
    handler = _report_handler.get()
    if handler:
        handler("output", message, end)
        return
    # CLI: print raw, no emoji, no colour — just the line
    _console.print(message, end=end, highlight=False)
    _console.file.flush()


def report_result(message: str, end: str = "\n") -> None:
    """
    Report a successful result.

    Args:
        message: The result message to display
        end: String appended after the message (default: "\n")
    """
    handler = _report_handler.get()
    if handler:
        handler("result", message, end)
        return
    _console.print(f" \u2705 {message}", style=Colors.WHITE, end=end)
    _console.file.flush()


def build_diff(old_str: str, new_str: str) -> str:
    """
    Build a unified diff between ``old_str`` and ``new_str``.

    Args:
        old_str: The text that was searched for (the "before" side).
        new_str: The replacement text (the "after" side).

    Returns:
        str: A unified diff (without trailing line terminators) suitable
            for syntax-highlighted display.
    """
    old_lines = old_str.splitlines()
    new_lines = new_str.splitlines()
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)


def report_diff(old_str: str, new_str: str, end: str = "\n") -> None:
    """
    Report the diff between ``old_str`` and ``new_str``.

    The unified diff is printed on the terminal with rich syntax
    highlighting (Pygments "diff" lexer). In web mode it is forwarded to
    the active report handler as a ``"diff"`` level event.

    Args:
        old_str: The text that was searched for (the "before" side).
        new_str: The replacement text (the "after" side).
        end: String appended after the message (default: "\n")
    """
    diff_text = build_diff(old_str, new_str)
    handler = _report_handler.get()
    if handler:
        handler("diff", diff_text, end)
        return
    from rich.syntax import Syntax

    _console.print(
        Syntax(diff_text or "", "diff", line_numbers=False, word_wrap=True),
        end=end,
    )
    _console.file.flush()


def report_error(message: str, end: str = "\n") -> None:
    """
    Report an error.

    Args:
        message: The error message to display
        end: String appended after the message (default: "\n")
    """
    handler = _report_handler.get()
    if handler:
        handler("error", message, end)
        return
    _console.print(f"\u274c {message}", style=Colors.RED, end=end)
    _console.file.flush()


def report_warning(message: str, end: str = "\n") -> None:
    """
    Report a warning.

    Args:
        message: The warning message to display
        end: String appended after the message (default: "\n")
    """
    handler = _report_handler.get()
    if handler:
        handler("warning", message, end)
        return
    _console.print(f"\u26a0\ufe0f  {message}", style=Colors.YELLOW, end=end)
    _console.file.flush()


def report_info(message: str, end: str = "\n") -> None:
    """
    Report an info message.

    Args:
        message: The info message to display
        end: String appended after the message (default: "\n")
    """
    handler = _report_handler.get()
    if handler:
        handler("info", message, end)
        return
    _console.print(f"\u2139\ufe0f  {message}", style=Colors.CYAN, end=end)
    _console.file.flush()
