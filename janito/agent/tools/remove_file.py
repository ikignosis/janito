import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase
from janito.i18n import tr


@register_tool(name="remove_file")
class RemoveFileTool(ToolBase):
    """
    Remove a file at the specified path.

    Args:
        file_path (str): Path to the file to remove.
        backup (bool, optional): If True, create a backup (.bak) before removing. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully removed the file at ..."
            - "❗ Cannot remove file: ..."
    """

    def run(self, file_path: str, backup: bool = False) -> str:
        original_path = file_path
        path = expand_path(file_path)
        disp_path = display_path(original_path)
        backup_path = None
        if not os.path.exists(path):
            self.report_error(
                tr("❌ File '{disp_path}' does not exist.", disp_path=disp_path)
            )
            return tr("❌ File '{disp_path}' does not exist.", disp_path=disp_path)
        if not os.path.isfile(path):
            self.report_error(
                tr("❌ Path '{disp_path}' is not a file.", disp_path=disp_path)
            )
            return tr("❌ Path '{disp_path}' is not a file.", disp_path=disp_path)
        try:
            if backup:
                backup_path = path + ".bak"
                shutil.copy2(path, backup_path)
            os.remove(path)
            self.report_success(
                tr("✅ File removed: '{disp_path}'", disp_path=disp_path)
            )
            msg = tr(
                "✅ Successfully removed the file at '{disp_path}'.",
                disp_path=disp_path,
            )
            if backup_path:
                msg += tr(
                    " (backup at {backup_disp})",
                    backup_disp=display_path(original_path + ".bak"),
                )
            return msg
        except Exception as e:
            self.report_error(tr("❌ Error removing file: {error}", error=e))
            return tr("❌ Error removing file: {error}", error=e)
