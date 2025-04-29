import os
import shutil
from janito.agent.tool_registry import register_tool

# from janito.agent.tools_utils.expand_path import expand_path
from janito.agent.tools_utils.utils import display_path
from janito.agent.tool_base import ToolBase
from janito.i18n import tr


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

    def run(
        self,
        src_path: str,
        dest_path: str,
        overwrite: bool = False,
        backup: bool = False,
    ) -> str:
        original_src = src_path
        original_dest = dest_path
        src = src_path  # Using src_path as is
        dest = dest_path  # Using dest_path as is
        disp_src = display_path(original_src)
        disp_dest = display_path(original_dest)
        backup_path = None
        if not os.path.exists(src):
            self.report_error(
                tr("❌ Source '{disp_src}' does not exist.", disp_src=disp_src)
            )
            return tr("❌ Source '{disp_src}' does not exist.", disp_src=disp_src)
        is_src_file = os.path.isfile(src)
        is_src_dir = os.path.isdir(src)
        if not (is_src_file or is_src_dir):
            self.report_error(
                tr(
                    "❌ Source path '{disp_src}' is neither a file nor a directory.",
                    disp_src=disp_src,
                )
            )
            return tr(
                "❌ Source path '{disp_src}' is neither a file nor a directory.",
                disp_src=disp_src,
            )
        if os.path.exists(dest):
            if not overwrite:
                self.report_error(
                    tr(
                        "❗ Destination '{disp_dest}' exists and overwrite is False.",
                        disp_dest=disp_dest,
                    )
                )
                return tr(
                    "❗ Destination '{disp_dest}' already exists and overwrite is False.",
                    disp_dest=disp_dest,
                )
            if backup:
                if os.path.isfile(dest):
                    backup_path = dest + ".bak"
                    shutil.copy2(dest, backup_path)
                elif os.path.isdir(dest):
                    backup_path = dest.rstrip("/\\") + ".bak.zip"
                    shutil.make_archive(dest.rstrip("/\\") + ".bak", "zip", dest)
            try:
                if os.path.isfile(dest):
                    os.remove(dest)
                elif os.path.isdir(dest):
                    shutil.rmtree(dest)
            except Exception as e:
                self.report_error(
                    tr("❌ Error removing destination before move: {error}", error=e)
                )
                return tr("❌ Error removing destination before move: {error}", error=e)
        try:
            self.report_info(
                tr(
                    "📝 Moving from '{disp_src}' to '{disp_dest}' ...",
                    disp_src=disp_src,
                    disp_dest=disp_dest,
                )
            )
            shutil.move(src, dest)
            self.report_success(tr("✅ Move complete."))
            msg = tr("✅ Move complete.")
            if backup_path:
                msg += tr(
                    " (backup at {backup_disp})",
                    backup_disp=display_path(
                        original_dest + (".bak" if is_src_file else ".bak.zip")
                    ),
                )
            return msg
        except Exception as e:
            self.report_error(tr("❌ Error moving: {error}", error=e))
            return tr("❌ Error moving: {error}", error=e)
