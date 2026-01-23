import os
from janito.tooling.path_utils import expand_path
import shutil


from janito.tooling.tool_utils import display_path
from janito.tooling.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr



class RemoveFileTool(ToolBase):
    permissions = ToolPermissions(write=True)

    def run(self, path: str) -> str:
        """
        Remove a file at the specified path.

        Args:
            path (str): Path to the file to remove.
        Returns:
            str: Status message indicating the result. Example:
                - "Successfully removed the file at ..."
                - "Cannot remove file: ..."
        """
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
