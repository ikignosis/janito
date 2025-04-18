from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

import shutil
import os



@register_tool(name="remove_directory")
class RemoveDirectoryTool(ToolBase):
    """Remove a directory. If recursive=False and directory not empty, raises error."""
    def call(self, directory: str, recursive: bool = False) -> str:
        self.report_info(f"🗃️ Removing directory: {directory} (recursive={recursive})")

        try:
            if recursive:
                shutil.rmtree(directory)
            else:
                os.rmdir(directory)
            self.report_success(f"✅ Removed: {directory}")
            return f"Directory removed: {directory}"
        except Exception as e:
            self.report_error(f" ❌ Error removing directory: {e}")
            return f"Error removing directory: {e}"


