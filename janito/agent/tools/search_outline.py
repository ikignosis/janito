from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import (
    pluralize,
    display_path,
    find_files_with_extensions,
)
from janito.agent.tools.outline_file.python_outline import parse_python_outline
from janito.agent.tools.outline_file.markdown_outline import parse_markdown_outline
import os
import re


@register_tool(name="search_outline")
class SearchOutlineTool(ToolBase):
    """
    Search for function, class, or header names in the outline of supported files (Python, Markdown).
    Faster than full-text search for code context queries. Supports substring and regex matching.

    Args:
        directories (list[str]): Directories to search in.
        pattern (str): Substring or regex to match in outline items (function/class/header names).
        file_types (list[str], optional): File extensions to include (default: ['.py', '.md']).
        regex (bool, optional): If True, use regex matching; otherwise, substring. Defaults to False.
        recursive (bool, optional): Whether to search subdirectories. Defaults to True.
    Returns:
        str: Newline-separated summary of matches: file, line, symbol/type, matched text.
    """

    def call(
        self,
        directories: list[str],
        pattern: str,
        file_types: list[str] = None,
        regex: bool = False,
        recursive: bool = True,
    ) -> str:
        if not pattern:
            self.report_warning(
                "⚠️ Warning: Empty search pattern provided. Operation skipped."
            )
            return "Warning: Empty search pattern provided. Operation skipped."
        if file_types is None:
            file_types = [".py", ".md"]
        files = find_files_with_extensions(directories, file_types, recursive=recursive)
        if not files:
            self.report_warning("No files found with supported extensions.")
            return "No files found with supported extensions."
        output = []
        matcher = re.compile(pattern) if regex else None
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                if ext == ".py":
                    outline_items = parse_python_outline(lines)
                    for item in outline_items:
                        name = item.get("name", "")
                        if (regex and matcher.search(name)) or (
                            not regex and pattern in name
                        ):
                            output.append(
                                f"{display_path(file_path)}:{item.get('start', '?')}: {item.get('type','?')}: {name}"
                            )
                elif ext == ".md":
                    outline_items = parse_markdown_outline(lines)
                    for item in outline_items:
                        title = item.get("title", "")
                        if (regex and matcher.search(title)) or (
                            not regex and pattern in title
                        ):
                            output.append(
                                f"{display_path(file_path)}:{item.get('line', '?')}: header: {title}"
                            )
            except Exception as e:
                self.report_warning(f"Error reading {file_path}: {e}")
        self.report_success(f"✅ {len(output)} {pluralize('match', len(output))} found")
        return "\n".join(output) if output else "No matches found."
