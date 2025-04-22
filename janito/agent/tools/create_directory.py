from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase
import os
import shutil


@register_tool(name="create_directory")
class CreateDirectoryTool(ToolBase):
    """
    Create a new directory at the specified path.

    Args:
        path (str): Path for the new directory.
        overwrite (bool, optional): Whether to overwrite if the directory exists. Defaults to False.
    Returns:
        str: Status message indicating the result. Example:
            - "\u2705 Successfully created the directory at ..."
            - "\u2757 Cannot create directory: ..."
    """

    def call(self, path: str, overwrite: bool = False) -> str:
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        self.report_info(
            f"\U0001f4c1 Creating directory: '{disp_path}' (overwrite={overwrite}) ... "
        )
        try:
            if os.path.exists(path):
                if not os.path.isdir(path):
                    self.report_error(
                        f"\u274c Path '{disp_path}' exists and is not a directory."
                    )
                    return f"\u274c Path '{disp_path}' exists and is not a directory."
                if not overwrite:
                    self.report_error(
                        f"\u2757 Directory '{disp_path}' already exists (overwrite=False)"
                    )
                    return (
                        f"\u2757 Cannot create directory: '{disp_path}' already exists."
                    )
                # Overwrite: remove existing directory
                shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)
            self.report_success(f"\u2705 Directory created at '{disp_path}'")
            return f"\u2705 Successfully created the directory at '{disp_path}'."
        except Exception as e:
            self.report_error(f"\u274c Error creating directory '{disp_path}': {e}")
            return f"\u274c Cannot create directory: {e}"
