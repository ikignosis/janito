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
        recursive: bool = True,
    ) -> str:
        if not pattern:
            self.report_warning(
                "⚠️ Warning: Empty search pattern provided. Operation skipped."
            )
            return "Warning: Empty search pattern provided. Operation skipped."
        output = []
        for directory in directories:
            info_str = f"🔎 Searching for text '{pattern}' in '{directory}'"
            if recursive is False:
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
                rel_path = os.path.relpath(root, directory)
                depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
                if not recursive and depth > 0:
                    break
                dirs, files = filter_ignored(root, dirs, files)
                for filename in files:
                    path = os.path.join(root, filename)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            for lineno, line in enumerate(f, 1):
                                if pattern in line:
                                    output.append(f"{path}:{lineno}: {line.strip()}")
                    except Exception:
                        continue
        self.report_success(f" ✅ {len(output)} {pluralize('line', len(output))} found")
        return "\n".join(output)
