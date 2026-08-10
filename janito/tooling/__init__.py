"""
Tooling package for AI tool support utilities.

This package provides infrastructure for AI tools including:
- Tool registry and schema generation
- Progress reporting utilities
- Base tool class
- Path utilities
"""

from .base_tool import BaseTool
from .decorator import is_tool, tool
from .path_utils import norm_path
from .prompting import get_prompt_handler, set_prompt_handler
from .reporter import (
    get_report_handler,
    report_diff,
    report_error,
    report_info,
    report_output,
    report_progress,
    report_result,
    report_start,
    report_warning,
    set_report_handler,
)
from .time_utils import format_duration_ms

# Note: tools_registry is not imported here to avoid circular imports
# with tools that depend on progress reporting utilities.

__all__ = [
    "BaseTool",
    "format_duration_ms",
    "get_prompt_handler",
    "get_report_handler",
    "is_tool",
    "norm_path",
    "report_diff",
    "report_error",
    "report_info",
    "report_output",
    "report_progress",
    "report_result",
    "report_start",
    "report_warning",
    "set_prompt_handler",
    "set_report_handler",
    "tool",
]
