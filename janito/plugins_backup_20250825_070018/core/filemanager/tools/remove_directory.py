from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import pluralize, display_path
from janito.i18n import tr
import shutil
import os
import zipfile
from janito.tools.path_utils import expand_path


@register_local_tool
class RemoveDirectoryTool(ToolBase):
    """
    Remove a directory.

    Args:
        path (str): Path to the directory to remove.
        recursive (bool, optional): If True, remove non-empty directories recursively (with backup). If False, only remove empty directories. Defaults to False.
    Returns:
        str: Status message indicating result. Example:
            - "Directory removed: /path/to/dir"
            - "Error removing directory: <error message>"
    """

    permissions = ToolPermissions(write=True)
    tool_name = "remove_directory"

    def run(self, path: str, recursive: bool = False) -> str:
        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(
            tr("🗃️ Remove directory '{disp_path}' ...", disp_path=disp_path),
            ReportAction.DELETE,
        )

        try:
            if recursive:

                shutil.rmtree(path)
            else:
                os.rmdir(path)
            self.report_success(
                tr("✅ 1 {dir_word}", dir_word=pluralize("directory", 1)),
                ReportAction.DELETE,
            )
            msg = tr("Directory removed: {disp_path}", disp_path=disp_path)

            return msg
        except Exception as e:
            self.report_error(
                tr(" ❌ Error removing directory: {error}", error=e),
                ReportAction.DELETE,
            )
            return tr("Error removing directory: {error}", error=e)
