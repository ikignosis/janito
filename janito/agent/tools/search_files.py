from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize

import os
from janito.agent.tools.gitignore_utils import filter_ignored


@register_tool(name="search_files")
class SearchFilesTool(ToolBase):
    """
    Search for a text pattern in all files within a directory and return matching lines. Respects .gitignore.

    Args:
        directories (list[str]): List of directories to search in.
        pattern (str): Plain text substring to search for in files. (Not a regular expression or glob pattern.)
        all_results (bool): If True, return all matches (no cap or warning). If False (default), cap at 100 results and warn if exceeded.
        recursive (bool): Whether to search recursively in subdirectories. Defaults to True.
    Returns:
        str: Matching lines from files as a newline-separated string, each formatted as 'filepath:lineno: line'. Example:
            - "/path/to/file.py:10: def my_function():"
            - "Warning: Empty search pattern provided. Operation skipped."
    """

    def call(
        self,
        directories: list[str],
        pattern: str,
        all_results: bool = False,
        recursive: bool = True,
    ) -> str:
        if not pattern:
            self.report_warning(
                "⚠️ Warning: Empty search pattern provided. Operation skipped."
            )
            return "Warning: Empty search pattern provided. Operation skipped."
        output = []
        max_results = 100
        for directory in directories:
            info_str = f"🔎 Searching for text '{pattern}' in '{directory}'"
            if recursive is False:  # Only show if user explicitly sets False
                info_str += f" (recursive={recursive})"
            self.report_info(info_str)
            if recursive:
                walker = os.walk(directory)
            else:
                # Only the top directory, not recursive
                dirs, files = filter_ignored(
                    directory, *os.walk(directory).__next__()[1:]
                )
                walker = [(directory, dirs, files)]
            for root, dirs, files in walker:
                dirs, files = filter_ignored(root, dirs, files)
                for filename in files:
                    path = os.path.join(root, filename)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            for lineno, line in enumerate(f, 1):
                                if pattern in line:
                                    output.append(f"{path}:{lineno}: {line.strip()}")
                                    if not all_results and len(output) >= max_results:
                                        break
                    except Exception:
                        continue
                if not all_results and len(output) >= max_results:
                    break
            if not all_results and len(output) >= max_results:
                break
        warning = ""
        if not all_results and len(output) >= max_results:
            warning = (
                "\n⚠️ Warning: Maximum result limit reached. Some matches may not be shown. "
                "You may want to expand your search pattern or set all_results=True to see all matches."
            )
            suffix = " (Max Reached)"
        else:
            suffix = ""
        self.report_success(
            f" ✅ {len(output)} {pluralize('line', len(output))}{suffix}"
        )
        return "\n".join(output) + warning
