import os
import shutil
from janito.agent.tool_registry import register_tool

# from janito.agent.tools_utils.expand_path import expand_path
from janito.agent.tools_utils.utils import display_path
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
        path = file_path  # Using file_path as is
        disp_path = display_path(original_path)
        backup_path = None
        # Report initial info about what is going to be removed
        self.report_info(tr("🗑️ Removing file '{disp_path}' ...", disp_path=disp_path))
        if not os.path.exists(path):
            self.report_error(tr("❌ File does not exist."))
            return tr("❌ File does not exist.")
        if not os.path.isfile(path):
            self.report_error(tr("❌ Path is not a file."))
            return tr("❌ Path is not a file.")
        try:
            if backup:
                backup_path = path + ".bak"
                shutil.copy2(path, backup_path)
            os.remove(path)
            self.report_success(tr("✅ File removed"))
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
