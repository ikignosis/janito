import os
from janito.tools.path_utils import expand_path
import shutil
from janito.tools.adapters.local.adapter import register_local_tool

from janito.tools.tool_utils import display_path
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr


@register_local_tool
class RemoveFileTool(ToolBase):
    """
    Remove a file at the specified path.

    Args:
        path (str): Path to the file to remove.
        backup (bool, optional): Deprecated. Backups are no longer created. Flag ignored.
    Returns:
        str: Status message indicating the result. Example:
            - "			 Successfully removed the file at ..."
            - "			 Cannot remove file: ..."
    """

    permissions = ToolPermissions(write=True)
    tool_name = "remove_file"

    def run(self, path: str, backup: bool = False) -> str:
        path = expand_path(path)
        disp_path = display_path(path)

        # Report initial info about what is going to be removed
        self.report_action(
            tr("🗑️ Remove file '{disp_path}' ...", disp_path=disp_path),
            ReportAction.DELETE,
        )
        if not os.path.exists(path):
            self.report_error(tr("❌ File does not exist."), ReportAction.DELETE)
            return tr("❌ File does not exist.")
        if not os.path.isfile(path):
            self.report_error(tr("❌ Path is not a file."), ReportAction.DELETE)
            return tr("❌ Path is not a file.")
        try:

            os.remove(path)
            self.report_success(tr("✅ File removed"), ReportAction.DELETE)
            msg = tr(
                "✅ Successfully removed the file at '{disp_path}'.",
                disp_path=disp_path,
            )

            return msg
        except Exception as e:
            self.report_error(
                tr("❌ Error removing file: {error}", error=e), ReportAction.DELETE
            )
            return tr("❌ Error removing file: {error}", error=e)
