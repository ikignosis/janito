#!/usr/bin/env python3
"""
Base Tool Class - A foundation for AI tools with built-in progress reporting.

This module provides a base class that tools can inherit from to get automatic
progress reporting capabilities and permission awareness.
"""

import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional



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
        # Get permission-based color for start messages only
        permissions = getattr(self, '_tool_permissions', "")
        if not permissions:
            color = "\033[36m"  # Cyan for no permissions (default)
        elif "x" in permissions:
            color = "\033[33m"  # Yellow for execute
        elif "w" in permissions:
            color = "\033[33m"  # Yellow for write (same as execute)
        elif "r" in permissions:
            color = "\033[32m"  # Green for read-only (safe)
        else:
            color = "\033[36m"  # Cyan as fallback
        
        reset_color = "\033[0m"
        # we put a space before the message to differentiate tool msgs from llm msgs
        colored_message = f" {color}{message}{reset_color}"
        print(colored_message, file=sys.stderr, end=end, flush=True)
    
    def report_progress(self, message: str, end: str = "\n") -> None:
        """
        Report ongoing progress of the tool operation.
        
        Args:
            message (str): The progress message to display
            end (str): String appended after the message (default: "\n")
        """
        print(f"{message}", file=sys.stderr, end=end, flush=True)
    
    def report_result(self, message: str, end: str = "\n") -> None:
        """
        Report intermediate or final results from the tool operation.
        
        Args:
            message (str): The result message to display
            end (str): String appended after the message (default: "\n")
        """
        white_color = "\033[37m"
        reset_color = "\033[0m"
        colored_message = f"{white_color} ✅ {message}{reset_color}"
        print(colored_message, file=sys.stderr, end=end, flush=True)
    
    def report_error(self, message: str, end: str = "\n") -> None:
        """
        Report an error during tool execution.
        
        Args:
            message (str): The error message to display
            end (str): String appended after the message (default: "\n")
        """
        print(f"❌ {message}", file=sys.stderr, end=end, flush=True)
    
    def report_warning(self, message: str, end: str = "\n") -> None:
        """
        Report a warning during tool execution.
        
        Args:
            message (str): The warning message to display
            end (str): String appended after the message (default: "\n")
        """
        print(f"⚠️{message}", file=sys.stderr, end=end, flush=True)
    
    def _get_permission_color(self) -> str:
        """
        Get ANSI color code based on tool permissions.
        
        Returns:
            str: ANSI color escape sequence
        """
        permissions = getattr(self, '_tool_permissions', "")
        if not permissions:
            return "\033[36m"  # Cyan for no permissions (default)
        elif "x" in permissions:
            return "\033[31m"  # Red for execute (dangerous)
        elif "w" in permissions:
            return "\033[33m"  # Orange for write
        elif "r" in permissions:
            return "\033[32m"  # Green for read-only (safe)
        else:
            return "\033[36m"  # Cyan as fallback
    
    def _report_with_permissions(self, message: str, end: str, report_type: str) -> None:
        """
        Internal method to report messages with permission-based coloring.
        
        Args:
            message (str): The message to display
            end (str): String appended after the message
            report_type (str): Type of report ("start", "progress", "result")
        """
        color = self._get_permission_color()
        reset_color = "\033[0m"
        if report_type == "result":
            white_color = "\033[37m"
            colored_message = f"{white_color}{message}{reset_color}"
        else:
            colored_message = f"{color}{message}{reset_color}"
        print(colored_message, file=sys.stderr, end=end, flush=True)