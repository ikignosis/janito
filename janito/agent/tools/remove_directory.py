from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import pluralize, display_path
from janito.i18n import tr
import shutil
import os
import zipfile


@register_tool(name="remove_directory")
class RemoveDirectoryTool(ToolBase):
    """
    Remove a directory.

    Args:
        file_path (str): Path to the directory to remove.
        recursive (bool, optional): If True, remove non-empty directories recursively (with backup). If False, only remove empty directories. Defaults to False.
    Returns:
        str: Status message indicating result. Example:
            - "Directory removed: /path/to/dir"
            - "Error removing directory: <error message>"
    """

    def run(self, file_path: str, recursive: bool = False) -> str:
        disp_path = display_path(file_path)
        self.report_info(
            tr("🗃️ Removing directory '{disp_path}' ...", disp_path=disp_path)
        )
        backup_zip = None
        try:
            if recursive:
                # Backup before recursive removal
                if os.path.exists(file_path) and os.path.isdir(file_path):
                    backup_zip = file_path.rstrip("/\\") + ".bak.zip"
                    with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(file_path):
                            for file in files:
                                abs_path = os.path.join(root, file)
                                rel_path = os.path.relpath(
                                    abs_path, os.path.dirname(file_path)
                                )
                                zipf.write(abs_path, rel_path)
                shutil.rmtree(file_path)
            else:
                os.rmdir(file_path)
            self.report_success(
                tr("✅ 1 {dir_word}", dir_word=pluralize("directory", 1))
            )
            msg = tr("Directory removed: {disp_path}", disp_path=disp_path)
            if backup_zip:
                msg += tr(" (backup at {backup_zip})", backup_zip=backup_zip)
            return msg
        except Exception as e:
            self.report_error(tr(" ❌ Error removing directory: {error}", error=e))
            return tr("Error removing directory: {error}", error=e)
