from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import (
    pluralize,
    display_path,
)
from janito.agent.tools.dir_walk_utils import walk_dir_with_gitignore

import fnmatch


@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """
    Find files in one or more directories matching a pattern. Respects .gitignore.

    Args:
        paths (str): String of one or more paths (space-separated) to search in. Each path can be a directory.
        pattern (str): File pattern(s) to match. Multiple patterns can be separated by spaces. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
        max_depth (int, optional): Maximum directory depth to search. If 0 (default), search is recursive with no depth limit. If >0, limits recursion to that depth. Setting max_depth=1 disables recursion (only top-level directory).
        max_results (int, optional): Maximum number of results to return. 0 means no limit (default).
    Returns:
        str: Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
            If max_results is reached, appends a note to the output.
    """

    def run(
        self,
        paths: str,
        pattern: str,
        max_depth: int = 0,
    ) -> str:
        import os

        if not pattern:
            self.report_warning(
                "⚠️  Warning: Empty file pattern provided. Operation skipped."
            )
            return "Warning: Empty file pattern provided. Operation skipped."

        output = set()
        patterns = pattern.split()
        for directory in paths.split():
            disp_path = display_path(directory)
            depth_msg = f" (max depth: {max_depth})" if max_depth > 0 else ""
            self.report_info(
                f"🔍 Searching for files '{pattern}' in '{disp_path}'{depth_msg} ..."
            )
            for root, dirs, files in walk_dir_with_gitignore(
                directory, max_depth=max_depth
            ):
                for pat in patterns:
                    for filename in fnmatch.filter(files, pat):
                        output.add(os.path.join(root, filename))
        self.report_success(
            f" \u2705 {len(output)} {pluralize('file', len(output))} found"
        )
        result = "\n".join(sorted(output))
        return result
