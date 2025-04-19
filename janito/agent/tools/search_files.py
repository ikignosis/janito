from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

import os



@register_tool(name="search_files")
class SearchFilesTool(ToolBase):
    """Search for a text pattern in all files within a directory and return matching lines."""
    def call(self, directories: list[str], pattern: str) -> str:
        """
        Search for a text pattern in all files within one or more directories and return matching lines.

        Args:
            directories (list[str]): List of directories to search in.
            pattern (str): Plain text substring to search for in files. (Not a regular expression or glob pattern.)

        Returns:
            str: Matching lines from files as a newline-separated string, each line formatted as 'filepath:lineno: line'.
        """
        if not pattern:
            self.report_warning("⚠️ Warning: Empty search pattern provided. Operation skipped.")
            return "Warning: Empty search pattern provided. Operation skipped."
        matches = []
        for directory in directories:
            self.report_info(f"🔎 Searching for text '{pattern}' in '{directory}'")
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    path = os.path.join(root, filename)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            for lineno, line in enumerate(f, 1):
                                if pattern in line:
                                    matches.append(f"{path}:{lineno}: {line.strip()}")
                    except Exception:
                        continue
        from janito.agent.tools.tools_utils import pluralize
        self.report_success(f" ✅ {len(matches)} {pluralize('line', len(matches))}")
        return '\n'.join(matches)


