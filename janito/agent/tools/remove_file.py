import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase


@register_tool(name="remove_file")
class RemoveFileTool(ToolBase):
    """
    Remove a file at the specified path.

    Args:
        file_path (str): Path to the file to remove.
        backup (bool, optional): If True, create a backup (.bak) before removing. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message indicating the result. Example:
            - "\u2705 Successfully removed the file at ..."
            - "\u2757 Cannot remove file: ..."
    """

    def call(self, file_path: str, backup: bool = False) -> str:
        original_path = file_path
        path = expand_path(file_path)
        disp_path = display_path(original_path, path)
        if not os.path.exists(path):
            self.report_error(f"\u274c File '{disp_path}' does not exist.")
            return f"\u274c File '{disp_path}' does not exist."
        if not os.path.isfile(path):
            self.report_error(f"\u274c Path '{disp_path}' is not a file.")
            return f"\u274c Path '{disp_path}' is not a file."
        try:
            if backup:
                shutil.copy2(path, path + ".bak")
            os.remove(path)
            self.report_success(f"\u2705 File removed: '{disp_path}'")
            return f"\u2705 Successfully removed the file at '{disp_path}'."
        except Exception as e:
            self.report_error(f"\u274c Error removing file: {e}")
            return f"\u274c Error removing file: {e}"
