from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize

import os
import re
from janito.agent.tools.gitignore_utils import filter_ignored


@register_tool(name="search_text")
class SearchTextTool(ToolBase):
    """
    Search for a text pattern (regex or plain string) in all files within one or more directories and return matching lines. Respects .gitignore.

    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory or a filename.
        pattern (str): Regex pattern or plain text substring to search for in files. Tries regex first, falls back to substring if regex is invalid.
        recursive (bool): Whether to search recursively in subdirectories (directories only). Defaults to True.
    Returns:
        str: Matching lines from files as a newline-separated string, each formatted as 'filepath:lineno: line'. Example:
            - "/path/to/file.py:10: def my_function():"
            - "Warning: Empty search pattern provided. Operation skipped."
    """

    def call(
        self,
        paths: str,
        pattern: str,
        recursive: bool = True,
    ) -> str:
        if not pattern:
            self.report_warning(
                "\u26a0\ufe0f Warning: Empty search pattern provided. Operation skipped."
            )
            return "Warning: Empty search pattern provided. Operation skipped."
        # Try compiling regex
        try:
            regex = re.compile(pattern)
            use_regex = True
        except re.error:
            regex = None
            use_regex = False
        output = []
        for directory in paths.split():
            info_str = (
                f"\ud83d\udd0e Searching for pattern '{pattern}' in '{directory}'"
            )
            if recursive is False:
                info_str += f" (recursive={recursive})"
            self.report_info(info_str)
            if recursive:
                walker = os.walk(directory)
            else:
                # Only the top directory, not recursive
                walk_result = next(os.walk(directory), None)
                if walk_result is None:
                    walker = [(directory, [], [])]
                else:
                    _, dirs, files = walk_result
                    dirs, files = filter_ignored(directory, dirs, files)
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
                                if use_regex:
                                    if regex.search(line):
                                        output.append(
                                            f"{path}:{lineno}: {line.strip()}"
                                        )
                                else:
                                    if pattern in line:
                                        output.append(
                                            f"{path}:{lineno}: {line.strip()}"
                                        )
                    except Exception:
                        continue
        self.report_success(
            f" \u2705 {len(output)} {pluralize('line', len(output))} found"
        )
        return "\n".join(output)
