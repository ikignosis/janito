import os
from janito.tools.path_utils import expand_path
import shutil
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import display_path
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr


@register_local_tool
class MoveFileTool(ToolBase):
    """
    Move a file or directory from src_path to dest_path.

    Args:
        src_path (str): Source file or directory path.
        dest_path (str): Destination file or directory path.
        overwrite (bool, optional): Whether to overwrite if the destination exists. Defaults to False.
        backup (bool, optional): Deprecated. No backups are created anymore. This flag is ignored. Defaults to False.
    Returns:
        str: Status message indicating the result.
    """

    permissions = ToolPermissions(read=True, write=True)
    tool_name = "move_file"

    def run(
        self,
        src_path: str,
        dest_path: str,
        overwrite: bool = False,
        backup: bool = False,
    ) -> str:
        src = expand_path(src_path)
        dest = expand_path(dest_path)
        original_src = src_path
        original_dest = dest_path
        disp_src = display_path(original_src)
        disp_dest = display_path(original_dest)
        backup_path = None

        valid, is_src_file, is_src_dir, err_msg = self._validate_source(src, disp_src)
        if not valid:
            return err_msg

        dest_result = self._handle_destination(dest, disp_dest, overwrite, backup)
        if dest_result is not None:
            backup_path, err_msg = dest_result
            if err_msg:
                return err_msg

        try:
            self.report_action(
                tr(
                    "📝 Moving from '{disp_src}' to '{disp_dest}' ...",
                    disp_src=disp_src,
                    disp_dest=disp_dest,
                ),
                ReportAction.UPDATE,
            )
            shutil.move(src, dest)
            self.report_success(tr("✅ Move complete."))
            msg = tr("✅ Move complete.")

            return msg
        except Exception as e:
            self.report_error(tr("❌ Error moving: {error}", error=e))
            return tr("❌ Error moving: {error}", error=e)

    def _validate_source(self, src, disp_src):
        if not os.path.exists(src):
            self.report_error(
                tr("❌ Source '{disp_src}' does not exist.", disp_src=disp_src)
            )
            return (
                False,
                False,
                False,
                tr("❌ Source '{disp_src}' does not exist.", disp_src=disp_src),
            )
        is_src_file = os.path.isfile(src)
        is_src_dir = os.path.isdir(src)
        if not (is_src_file or is_src_dir):
            self.report_error(
                tr(
                    "❌ Source path '{disp_src}' is neither a file nor a directory.",
                    disp_src=disp_src,
                )
            )
            return (
                False,
                False,
                False,
                tr(
                    "❌ Source path '{disp_src}' is neither a file nor a directory.",
                    disp_src=disp_src,
                ),
            )
        return True, is_src_file, is_src_dir, None

    def _handle_destination(self, dest, disp_dest, overwrite, backup):
        backup_path = None
        if os.path.exists(dest):
            if not overwrite:
                self.report_error(
                    tr(
                        "❗ Destination '{disp_dest}' exists and overwrite is False.",
                        disp_dest=disp_dest,
                    ),
                    ReportAction.UPDATE,
                )
                return None, tr(
                    "❗ Destination '{disp_dest}' already exists and overwrite is False.",
                    disp_dest=disp_dest,
                )

            try:
                if os.path.isfile(dest):
                    os.remove(dest)
                elif os.path.isdir(dest):
                    shutil.rmtree(dest)
            except Exception as e:
                self.report_error(
                    tr("❌ Error removing destination before move: {error}", error=e),
                    ReportAction.UPDATE,
                )
                return None, tr(
                    "❌ Error removing destination before move: {error}", error=e
                )
        return backup_path, None
