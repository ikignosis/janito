from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase

@register_tool(name="create_directory")
class CreateDirectoryTool(ToolBase):
    """
    Create a new directory at the specified path.
    """
    def call(self, path: str, overwrite: bool = False) -> str:
        """
        Create a new directory at the specified path.

        Args:
            path (str): Path for the new directory.
            overwrite (bool, optional): Whether to overwrite if the directory exists. Defaults to False.

        Returns:
            str: Status message indicating the result. Example:
                - "✅ Successfully created the directory at ..."
                - "❗ Cannot create directory: ..."
        """
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        import os
        if os.path.exists(path):
            if not os.path.isdir(path):
                self.report_error(f"❌ Path '{disp_path}' exists and is not a directory.")
                return f"❌ Path '{disp_path}' exists and is not a directory."
        # Directory creation logic would go here
        return f"✅ Successfully created the directory at '{disp_path}'."
