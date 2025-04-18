from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


import os
import fnmatch

@register_tool(name="find_files")
class FindFilesTool(ToolBase):
    """Find files in a directory matching a pattern."""
    def call(self, directory: str, pattern: str, recursive: bool=False, max_results: int=100) -> str:
        import os
        def _display_path(path):
            import os
            if os.path.isabs(path):
                return path
            return os.path.relpath(path)
        disp_path = _display_path(directory)
        rec = "recursively" if recursive else "non-recursively"
        self.report_info(f"🔍 Searching for files in '{disp_path}' matching pattern '{pattern}' {rec}, max {max_results}")
        matches = []
        for root, dirs, files in os.walk(directory):
            for filename in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, filename))
                if len(matches) >= max_results:
                    break
            if not recursive:
                break
        self.report_success(f"✅ {len(matches)} files found")
        return "\n".join(matches)


