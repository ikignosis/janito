#!/usr/bin/env python3
"""
Base Tool Class - A foundation for AI tools with built-in progress reporting.

This module provides a base class that tools can inherit from to get automatic
progress reporting capabilities and permission awareness.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from rich.console import Console

# Shared console for stderr output (no auto-highlighting or markup interpretation)
_console = Console(stderr=True, highlight=False, markup=False)


class BaseTool(ABC):
    """
    Base class for AI tools with built-in progress reporting and permissions.
    
    Tools should inherit from this class and implement the `run` method.
    The class automatically provides progress reporting methods that are
    aware of the tool's declared permissions.
    """
    
    # Class-level permissions attribute (set by the @tool decorator)
    _tool_permissions: str = ""

    # Optional human-readable explanation for why the tool was not loaded.
    # Tools may set this inside should_load() before returning False.
    _load_skip_reason: str = ""

    def __init__(self):
        """Initialize the base tool."""
        pass

    @classmethod
    def should_load(cls) -> bool:
        """
        Validate whether this tool should be loaded and made available.

        Tools can override this class method to check runtime requirements
        such as external binaries, platform support, environment variables,
        or credentials. Tools returning False are skipped during discovery:
        they are never registered, advertised to the LLM, or callable.

        When returning False, tools may set `cls._load_skip_reason` to a
        human-readable explanation (used for diagnostics, e.g. /tools).

        Returns:
            bool: True if the tool should be loaded (default), False to skip it
        """
        return True

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool's main functionality.
        
        This method must be implemented by subclasses.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Dict[str, Any]: Tool result dictionary
        """
        pass
    
    def report_start(self, message: str, end: str = "\n") -> None:
        """
        Report that the tool operation is starting.
        
        Args:
            message (str): The message to display
            end (str): String appended after the message (default: "\n")
        """
        # Get permission-based style for start messages only
        permissions = getattr(self, '_tool_permissions', "")
        if not permissions:
            style = "cyan"  # Cyan for no permissions (default)
        elif "x" in permissions:
            style = "yellow"  # Yellow for execute
        elif "w" in permissions:
            style = "yellow"  # Yellow for write (same as execute)
        elif "r" in permissions:
            style = "green"  # Green for read-only (safe)
        else:
            style = "cyan"  # Cyan as fallback
        
        # we put a space before the message to differentiate tool msgs from llm msgs
        _console.print(f" {message}", style=style, end=end)
        _console.file.flush()
    
    def report_progress(self, message: str, end: str = "\n") -> None:
        """
        Report ongoing progress of the tool operation.
        
        Args:
            message (str): The progress message to display
            end (str): String appended after the message (default: "\n")
        """
        _console.print(f"{message}", end=end)
        _console.file.flush()
    
    def report_result(self, message: str, end: str = "\n") -> None:
        """
        Report intermediate or final results from the tool operation.
        
        Args:
            message (str): The result message to display
            end (str): String appended after the message (default: "\n")
        """
        _console.print(f" \u2705 {message}", style="white", end=end)
        _console.file.flush()
    
    def report_error(self, message: str, end: str = "\n") -> None:
        """
        Report an error during tool execution.
        
        Args:
            message (str): The error message to display
            end (str): String appended after the message (default: "\n")
        """
        _console.print(f"\u274c {message}", style="red", end=end)
        _console.file.flush()
    
    def report_warning(self, message: str, end: str = "\n") -> None:
        """
        Report a warning during tool execution.
        
        Args:
            message (str): The warning message to display
            end (str): String appended after the message (default: "\n")
        """
        _console.print(f"\u26a0\ufe0f{message}", style="yellow", end=end)
        _console.file.flush()
    
    def _get_permission_color(self) -> str:
        """
        Get rich style name based on tool permissions.
        
        Returns:
            str: Rich style name
        """
        permissions = getattr(self, '_tool_permissions', "")
        if not permissions:
            return "cyan"  # Cyan for no permissions (default)
        elif "x" in permissions:
            return "red"  # Red for execute (dangerous)
        elif "w" in permissions:
            return "yellow"  # Yellow for write
        elif "r" in permissions:
            return "green"  # Green for read-only (safe)
        else:
            return "cyan"  # Cyan as fallback
    
    def _report_with_permissions(self, message: str, end: str, report_type: str) -> None:
        """
        Internal method to report messages with permission-based coloring.
        
        Args:
            message (str): The message to display
            end (str): String appended after the message
            report_type (str): Type of report ("start", "progress", "result")
        """
        if report_type == "result":
            style = "white"
        else:
            style = self._get_permission_color()
        _console.print(message, style=style, end=end)
        _console.file.flush()
