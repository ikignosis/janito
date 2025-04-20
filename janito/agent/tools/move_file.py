import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase


@register_tool(name="move_file")
class MoveFileTool(ToolBase):
    """
    Move a file from src_path to dest_path.
    """

    def call(self, src_path: str, dest_path: str, overwrite: bool = False) -> str:
        """
        Move a file from src_path to dest_path.

        Args:
            src_path (str): Source file path.
            dest_path (str): Destination file path.
            overwrite (bool, optional): Whether to overwrite if the destination exists. Defaults to False.

        Returns:
            str: Status message indicating the result.
        """
        original_src = src_path
        original_dest = dest_path
        src = expand_path(src_path)
        dest = expand_path(dest_path)
        disp_src = display_path(original_src, src)
        disp_dest = display_path(original_dest, dest)

        if not os.path.exists(src):
            self.report_error(f"\u274c Source file '{disp_src}' does not exist.")
            return f"\u274c Source file '{disp_src}' does not exist."
        if not os.path.isfile(src):
            self.report_error(f"\u274c Source path '{disp_src}' is not a file.")
            return f"\u274c Source path '{disp_src}' is not a file."
        if os.path.exists(dest):
            if not overwrite:
                self.report_error(
                    f"\u2757 Destination '{disp_dest}' exists and overwrite is False."
                )
                return f"\u2757 Destination '{disp_dest}' already exists and overwrite is False."
            if os.path.isdir(dest):
                self.report_error(f"\u274c Destination '{disp_dest}' is a directory.")
                return f"\u274c Destination '{disp_dest}' is a directory."
        try:
            shutil.move(src, dest)
            self.report_success(f"\u2705 File moved from '{disp_src}' to '{disp_dest}'")
            return f"\u2705 Successfully moved the file from '{disp_src}' to '{disp_dest}'."
        except Exception as e:
            self.report_error(f"\u274c Error moving file: {e}")
            return f"\u274c Error moving file: {e}"
