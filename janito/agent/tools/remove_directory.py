from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
import shutil
import os

from janito.agent.tools.rich_utils import print_info, print_success, print_error

class RemoveDirectoryTool(ToolBase):
    """Remove a directory. If recursive=False and directory not empty, raises error."""
    def call(self, directory: str, recursive: bool = False) -> str:
        print_info(f"🗃️ Removing directory: {directory} (recursive={recursive})", end="")
        self.update_progress(f"Removing directory: {directory} (recursive={recursive})")
        try:
            if recursive:
                shutil.rmtree(directory)
            else:
                os.rmdir(directory)
            print_success(f"✅ Directory removed: {directory}")
            return f"Directory removed: {directory}"
        except Exception as e:
            print_error(f"\u274c Error removing directory: {e}")
            return f"Error removing directory: {e}"

ToolHandler.register_tool(RemoveDirectoryTool, name="remove_directory")
