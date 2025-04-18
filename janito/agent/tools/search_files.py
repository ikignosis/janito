from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

import os



@register_tool(name="search_files")
class SearchFilesTool(ToolBase):
    """Search for a text pattern in all files within a directory and return matching lines."""
    def call(self, directory: str, pattern: str) -> str:
        self.report_info(f"🔎 Searching for pattern '{pattern}' in directory {directory}")

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
        self.report_success(f"✅ Found {len(matches)} matches")
        return '\n'.join(matches)


