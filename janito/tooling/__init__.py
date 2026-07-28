"""
Tooling package for AI tool support utilities.

This package provides infrastructure for AI tools including:
- Tool registry and schema generation
- Progress reporting utilities
- Base tool class
- Path utilities
"""

from .base_tool import BaseTool
from .path_utils import norm_path
from .reporter import (
    get_report_handler,
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
    "get_report_handler",
    "norm_path",
    "report_error",
    "report_info",
    "report_output",
    "report_progress",
    "report_result",
    "report_start",
    "report_warning",
    "set_report_handler",
]
