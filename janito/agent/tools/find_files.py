from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


import os
import fnmatch

@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """Find files in a directory matching a pattern."""
    def call(self, directories: list[str], pattern: str, recursive: bool=False, max_results: int=100) -> str:
        """
        Find files in one or more directories matching a pattern.

        Args:
            directories (list[str]): List of directories to search in.
            pattern (str): File pattern to match. Uses Unix shell-style wildcards (fnmatch), e.g., '*.py', 'data_??.csv', '[a-z]*.txt'.
            recursive (bool, optional): Whether to search recursively in subdirectories. Defaults to False.
            max_results (int, optional): Maximum number of results to return. Defaults to 100.

        Returns:
            str: List of matching file paths as a newline-separated string.
        """
        import os
        if not pattern:
            self.report_warning("⚠️ Warning: Empty file pattern provided. Operation skipped.")
            return "Warning: Empty file pattern provided. Operation skipped."
        from janito.agent.tools.tools_utils import display_path
        matches = []
        rec = "recursively" if recursive else "non-recursively"
        for directory in directories:
            disp_path = display_path(directory)
            self.report_info(f"🔍 Searching for files '{pattern}' in '{disp_path}'")
            for root, dirs, files in os.walk(directory):
                for filename in fnmatch.filter(files, pattern):
                    matches.append(os.path.join(root, filename))
                    if len(matches) >= max_results:
                        break
                if not recursive:
                    break
            if len(matches) >= max_results:
                break
        from janito.agent.tools.tools_utils import pluralize
        self.report_success(f" ✅ {len(matches)} {pluralize('file', len(matches))}")
        return "\n".join(matches)


