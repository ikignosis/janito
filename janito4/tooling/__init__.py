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
    report_start,
    report_progress,
    report_result,
    report_error,
    report_warning,
    report_info,
)

# Note: tools_registry is not imported here to avoid circular imports
# with tools that depend on progress reporting utilities.

__all__ = [
    "BaseTool",
    "norm_path",
    "report_start",
    "report_progress",
    "report_result",
    "report_error",
    "report_warning",
    "report_info",
]