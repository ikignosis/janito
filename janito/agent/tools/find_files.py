from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success
import os
import fnmatch

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
        print_info(f"🔍 Scanning '{disp_path}' for files matching pattern '{pattern}' ({rec}, max {max_results})", end="")
        self.update_progress(f"Searching for files in {directory} matching {pattern}")
        matches = []
        for root, dirs, files in os.walk(directory):
            for filename in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, filename))
                if len(matches) >= max_results:
                    break
            if not recursive:
                break
        print_success(f"✅ {len(matches)} files found")
        return "\n".join(matches)

ToolHandler.register_tool(FindFilesTool, name="find_files")
