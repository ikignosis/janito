from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import (
    pluralize,
    display_path,
    find_files_with_extensions,
)

import fnmatch


@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """
    Find files in one or more directories matching a pattern. Respects .gitignore.

    Args:
        directories (list[str]): List of directories to search in.
        pattern (str): File pattern to match. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
        recursive (bool, optional): Whether to search recursively in subdirectories. Defaults to True.
    Returns:
        str: Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
    """

    def call(
        self,
        directories: list[str],
        pattern: str,
        recursive: bool = True,
    ) -> str:
        import os

        if not pattern:
            self.report_warning(
                "⚠️ Warning: Empty file pattern provided. Operation skipped."
            )
            return "Warning: Empty file pattern provided. Operation skipped."

        output = []
        for directory in directories:
            disp_path = display_path(directory)
            self.report_info(f"🔍 Searching for files '{pattern}' in '{disp_path}' ...")
            # If pattern is a simple extension (e.g. '*.py'), use the new utility
            if (
                pattern.startswith("*.")
                and pattern.count("*") == 1
                and pattern.count(".") == 1
            ):
                ext = pattern[1:]  # '.py'
                files = find_files_with_extensions(
                    [directory], [ext], recursive=recursive
                )
                output.extend(files)
            else:
                for root, dirs, files in os.walk(directory):
                    rel_path = os.path.relpath(root, directory)
                    depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
                    if not recursive and depth > 0:
                        break
                    from janito.agent.tools.gitignore_utils import filter_ignored

                    dirs, files = filter_ignored(root, dirs, files)
                    for filename in fnmatch.filter(files, pattern):
                        output.append(os.path.join(root, filename))
        self.report_success(f" ✅ {len(output)} {pluralize('file', len(output))} found")
        return "\n".join(output)
