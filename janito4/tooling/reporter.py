#!/usr/bin/env python3
"""
Standalone Progress Reporter - For use outside of BaseTool classes.

This module provides progress reporting functions that can be used
by any code that needs to report progress to the user, including MCP tools.
"""

import sys
from typing import Optional


# ANSI color codes
class Colors:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    WHITE = "\033[37m"
    RESET = "\033[0m"


def report_start(message: str, end: str = "\n", color: str = Colors.CYAN) -> None:
    """
    Report that an operation is starting.
    
    Args:
        message: The message to display
        end: String appended after the message (default: "\n")
        color: The color to use (default: CYAN)
    """
    colored_message = f" {color}🔄 {message}{Colors.RESET}"
    print(colored_message, file=sys.stderr, end=end, flush=True)


def report_progress(message: str, end: str = "\n") -> None:
    """
    Report ongoing progress of an operation.
    
    Args:
        message: The progress message to display
        end: String appended after the message (default: "\n")
    """
    print(f"{message}", file=sys.stderr, end=end, flush=True)


def report_result(message: str, end: str = "\n") -> None:
    """
    Report a successful result.
    
    Args:
        message: The result message to display
        end: String appended after the message (default: "\n")
    """
    colored_message = f"{Colors.WHITE} ✅ {message}{Colors.RESET}"
    print(colored_message, file=sys.stderr, end=end, flush=True)


def report_error(message: str, end: str = "\n") -> None:
    """
    Report an error.
    
    Args:
        message: The error message to display
        end: String appended after the message (default: "\n")
    """
    print(f"❌ {message}", file=sys.stderr, end=end, flush=True)


def report_warning(message: str, end: str = "\n") -> None:
    """
    Report a warning.
    
    Args:
        message: The warning message to display
        end: String appended after the message (default: "\n")
    """
    print(f"⚠️  {message}", file=sys.stderr, end=end, flush=True)


def report_info(message: str, end: str = "\n") -> None:
    """
    Report an info message.
    
    Args:
        message: The info message to display
        end: String appended after the message (default: "\n")
    """
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.RESET}", file=sys.stderr, end=end, flush=True)
