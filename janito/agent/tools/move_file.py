import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase


@register_tool(name="move_file")
class MoveFileTool(ToolBase):
    """
    Move a file from src_path to dest_path.

    Args:
        src_path (str): Source file path.
        dest_path (str): Destination file path.
        overwrite (bool, optional): Whether to overwrite if the destination exists. Defaults to False.
        backup (bool, optional): If True, create a backup (.bak) of the destination before moving if it exists. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message indicating the result.
    """

    def call(
        self,
        src_path: str,
        dest_path: str,
        overwrite: bool = False,
        backup: bool = False,
    ) -> str:
        original_src = src_path
        original_dest = dest_path
        src = expand_path(src_path)
        dest = expand_path(dest_path)
        disp_src = display_path(original_src, src)
        disp_dest = display_path(original_dest, dest)
        backup_path = None

        if not os.path.exists(src):
            self.report_error(f"❌ Source file '{disp_src}' does not exist.")
            return f"❌ Source file '{disp_src}' does not exist."
        if not os.path.isfile(src):
            self.report_error(f"❌ Source path '{disp_src}' is not a file.")
            return f"❌ Source path '{disp_src}' is not a file."
        if os.path.exists(dest):
            if not overwrite:
                self.report_error(
                    f"❗ Destination '{disp_dest}' exists and overwrite is False."
                )
                return f"❗ Destination '{disp_dest}' already exists and overwrite is False."
            if os.path.isdir(dest):
                self.report_error(f"❌ Destination '{disp_dest}' is a directory.")
                return f"❌ Destination '{disp_dest}' is a directory."
            if backup:
                backup_path = dest + ".bak"
                shutil.copy2(dest, backup_path)
        try:
            shutil.move(src, dest)
            self.report_success(f"✅ File moved from '{disp_src}' to '{disp_dest}'")
            msg = f"✅ Successfully moved the file from '{disp_src}' to '{disp_dest}'."
            if backup_path:
                msg += (
                    f" (backup at {display_path(original_dest + '.bak', backup_path)})"
                )
            return msg
        except Exception as e:
            self.report_error(f"❌ Error moving file: {e}")
            return f"❌ Error moving file: {e}"
