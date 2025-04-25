import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase


@register_tool(name="move_file")
class MoveFileTool(ToolBase):
    """
    Move a file or directory from src_path to dest_path.

    Args:
        src_path (str): Source file or directory path.
        dest_path (str): Destination file or directory path.
        overwrite (bool, optional): Whether to overwrite if the destination exists. Defaults to False.
        backup (bool, optional): If True, create a backup (.bak for files, .bak.zip for directories) of the destination before moving if it exists. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
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
            self.report_error(f"❌ Source '{disp_src}' does not exist.")
            return f"❌ Source '{disp_src}' does not exist."

        is_src_file = os.path.isfile(src)
        is_src_dir = os.path.isdir(src)
        if not (is_src_file or is_src_dir):
            self.report_error(
                f"❌ Source path '{disp_src}' is neither a file nor a directory."
            )
            return f"❌ Source path '{disp_src}' is neither a file nor a directory."

        if os.path.exists(dest):
            if not overwrite:
                self.report_error(
                    f"❗ Destination '{disp_dest}' exists and overwrite is False."
                )
                return f"❗ Destination '{disp_dest}' already exists and overwrite is False."
            # Backup logic
            if backup:
                if os.path.isfile(dest):
                    backup_path = dest + ".bak"
                    shutil.copy2(dest, backup_path)
                elif os.path.isdir(dest):
                    backup_path = dest.rstrip("/\\") + ".bak.zip"
                    shutil.make_archive(dest.rstrip("/\\") + ".bak", "zip", dest)
            # Remove destination before move
            try:
                if os.path.isfile(dest):
                    os.remove(dest)
                elif os.path.isdir(dest):
                    shutil.rmtree(dest)
            except Exception as e:
                self.report_error(f"❌ Error removing destination before move: {e}")
                return f"❌ Error removing destination before move: {e}"

        try:
            shutil.move(src, dest)
            self.report_success(f"✅ Moved from '{disp_src}' to '{disp_dest}'")
            msg = f"✅ Successfully moved from '{disp_src}' to '{disp_dest}'."
            if backup_path:
                msg += f" (backup at {display_path(original_dest + ('.bak' if is_src_file else '.bak.zip'), backup_path)})"
            return msg
        except Exception as e:
            self.report_error(f"❌ Error moving: {e}")
            return f"❌ Error moving: {e}"
