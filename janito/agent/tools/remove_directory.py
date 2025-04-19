from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

import shutil
import os



@register_tool(name="remove_directory")
class RemoveDirectoryTool(ToolBase):
    """Remove a directory. If recursive=False and directory not empty, raises error."""
    def call(self, directory: str, recursive: bool = False) -> str:
        """
        Remove a directory.

        Args:
            directory (str): Path to the directory to remove.
            recursive (bool, optional): Remove recursively if True. Defaults to False.

        Returns:
            str: Status message indicating result.
        """
        self.report_info(f"🗃️  Removing directory: {directory} (recursive={recursive})")

        try:
            if recursive:
                shutil.rmtree(directory)
            else:
                os.rmdir(directory)
            from janito.agent.tools.tools_utils import pluralize
            self.report_success(f"✅ 1 {pluralize('directory', 1)}")
            return f"Directory removed: {directory}"
        except Exception as e:
            self.report_error(f" ❌ Error removing directory: {e}")
            return f"Error removing directory: {e}"


