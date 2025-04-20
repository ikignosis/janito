from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize

import os
from janito.agent.tools.gitignore_utils import filter_ignored

@register_tool(name="search_files")
class SearchFilesTool(ToolBase):
    """Search for a text pattern in all files within a directory and return matching lines. Respects .gitignore."""
    def call(self, directories: list[str], pattern: str, max_results: int=100) -> str:
        """
        Search for a text pattern in all files within one or more directories and return matching lines.

        Args:
            directories (list[str]): List of directories to search in.
            pattern (str): Plain text substring to search for in files. (Not a regular expression or glob pattern.)
            max_results (int): Maximum number of results to return. Defaults to 100.

        Returns:
            str: Matching lines from files as a newline-separated string, each formatted as 'filepath:lineno: line'. Example:
                - "/path/to/file.py:10: def my_function():"
                - "Warning: Empty search pattern provided. Operation skipped."
        """
        if not pattern:
            self.report_warning("⚠️ Warning: Empty search pattern provided. Operation skipped.")
            return "Warning: Empty search pattern provided. Operation skipped."
        output = []
        for directory in directories:
            self.report_info(f"🔎 Searching for text '{pattern}' in '{directory}'")
            for root, dirs, files in os.walk(directory):
                dirs, files = filter_ignored(root, dirs, files)
                for filename in files:
                    path = os.path.join(root, filename)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            for lineno, line in enumerate(f, 1):
                                if pattern in line:
                                    output.append(f"{path}:{lineno}: {line.strip()}")
                                    if len(output) >= max_results:
                                        break
                    except Exception:
                        continue
                if len(output) >= max_results:
                    break
            if len(output) >= max_results:
                break
        warning = ""
        if len(output) >= max_results:
            warning = "\n⚠️ Warning: Maximum result limit reached. Some matches may not be shown."
            suffix = " (Max Reached)"
        else:
            suffix = ""
        self.report_success(f" ✅ {len(output)} {pluralize('line', len(output))}{suffix}")
        return '\n'.join(output) + warning


