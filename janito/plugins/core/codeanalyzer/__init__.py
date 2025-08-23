"""
Code Analyzer Plugin

Tools for understanding and searching code structure.
"""

from typing import List, Optional


def get_file_outline(path: str) -> str:
    """Get file structure (classes, functions, etc.)"""
    return f"get_file_outline(path='{path}')"


get_file_outline.tool_name = "get_file_outline"


def search_outline(path: str) -> str:
    """Search within file outlines"""
    return f"search_outline(path='{path}')"


search_outline.tool_name = "search_outline"


def search_text(
    paths: str,
    query: str,
    use_regex: bool = False,
    case_sensitive: bool = True,
    max_depth: Optional[int] = None,
) -> str:
    """Full-text search across files with regex support"""
    return f"search_text(paths='{paths}', query='{query}', regex={use_regex})"


search_text.tool_name = "search_text"


# Plugin metadata
__plugin_name__ = "core.codeanalyzer"
__plugin_description__ = "Code analysis and structure understanding"
__plugin_tools__ = [get_file_outline, search_outline, search_text]
