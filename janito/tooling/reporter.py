#!/usr/bin/env python3
"""
Standalone Progress Reporter - For use outside of BaseTool classes.

This module provides progress reporting functions that can be used
by any code that needs to report progress to the user, including MCP tools.
"""

from rich.console import Console

# Shared console for stderr output (no auto-highlighting or markup interpretation)
_console = Console(stderr=True, highlight=False, markup=False)


# Rich style names (replaces raw ANSI escape codes)
class Colors:
    CYAN = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    WHITE = "white"
    RESET = ""


def report_start(message: str, end: str = "\n", color: str = Colors.CYAN) -> None:
    """
    Report that an operation is starting.
    
    Args:
        message: The message to display
        end: String appended after the message (default: "\n")
        color: The rich style to use (default: CYAN)
    """
    _console.print(f" \U0001f504 {message}", style=color, end=end)
    _console.file.flush()


def report_progress(message: str, end: str = "\n") -> None:
    """
    Report ongoing progress of an operation.
    
    Args:
        message: The progress message to display
        end: String appended after the message (default: "\n")
    """
    _console.print(f"{message}", end=end)
    _console.file.flush()


def report_result(message: str, end: str = "\n") -> None:
    """
    Report a successful result.
    
    Args:
        message: The result message to display
        end: String appended after the message (default: "\n")
    """
    _console.print(f" \u2705 {message}", style=Colors.WHITE, end=end)
    _console.file.flush()


def report_error(message: str, end: str = "\n") -> None:
    """
    Report an error.
    
    Args:
        message: The error message to display
        end: String appended after the message (default: "\n")
    """
    _console.print(f"\u274c {message}", style=Colors.RED, end=end)
    _console.file.flush()


def report_warning(message: str, end: str = "\n") -> None:
    """
    Report a warning.
    
    Args:
        message: The warning message to display
        end: String appended after the message (default: "\n")
    """
    _console.print(f"\u26a0\ufe0f  {message}", style=Colors.YELLOW, end=end)
    _console.file.flush()


def report_info(message: str, end: str = "\n") -> None:
    """
    Report an info message.
    
    Args:
        message: The info message to display
        end: String appended after the message (default: "\n")
    """
    _console.print(f"\u2139\ufe0f  {message}", style=Colors.CYAN, end=end)
    _console.file.flush()
