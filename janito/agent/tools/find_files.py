from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


import fnmatch
from janito.agent.tools.gitignore_utils import filter_ignored

@register_tool(name="find_files")
class FindFilesTool(ToolBase):

    def call(self, directories: list[str], pattern: str, recursive: bool=False, max_results: int=100) -> str:
        """
        Find files in one or more directories matching a pattern. Respects .gitignore.

        Args:
            directories: List of directories to search in.
            pattern: File pattern to match. Uses Unix shell-style wildcards (fnmatch), e.g. '*.py', 'data_??.csv', '[a-z]*.txt'.
            recursive: Whether to search recursively in subdirectories. Defaults to False.
            max_results: Maximum number of results to return. Defaults to 100.
        Returns:
            Newline-separated list of matching file paths. Example:
            "/path/to/file1.py\n/path/to/file2.py"
            "Warning: Empty file pattern provided. Operation skipped."
        """
        import os
        if not pattern:
            self.report_warning("⚠️ Warning: Empty file pattern provided. Operation skipped.")
            return "Warning: Empty file pattern provided. Operation skipped."
        from janito.agent.tools.tools_utils import display_path
        output = []
        rec = "recursively" if recursive else "non-recursively"
        for directory in directories:
            disp_path = display_path(directory)
            self.report_info(f"🔍 Searching for files '{pattern}' in '{disp_path}'")
            for root, dirs, files in os.walk(directory):
                dirs, files = filter_ignored(root, dirs, files)
                for filename in fnmatch.filter(files, pattern):
                    output.append(os.path.join(root, filename))
                    if len(output) >= max_results:
                        break
                if not recursive or len(output) >= max_results:
                    break
            if len(output) >= max_results:
                break
        warning = ""
        if len(output) >= max_results:
            warning = "\n⚠️ Warning: Maximum result limit reached. Some matches may not be shown."
            suffix = " (Max Reached)"
        else:
            suffix = ""
        self.report_success(f" ✅ {len(output)} {pluralize('file', len(output))}{suffix}")
        return "\n".join(output) + warning


from janito.agent.tools.tools_utils import pluralize
