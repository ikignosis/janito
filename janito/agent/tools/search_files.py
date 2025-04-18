from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
import os

from janito.agent.tools.rich_utils import print_info, print_success

class SearchFilesTool(ToolBase):
    """Search for a text pattern in all files within a directory and return matching lines."""
    def call(self, directory: str, pattern: str) -> str:
        print_info(f"🔎 Searching for pattern '{pattern}' in directory {directory}")
        self.update_progress(f"Searching for pattern '{pattern}' in directory {directory}")
        matches = []
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
        print_success(f"\u2705 {len(matches)} matches found")
        return '\n'.join(matches)

ToolHandler.register_tool(SearchFilesTool, name="search_files")
