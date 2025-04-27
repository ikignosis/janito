from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize

import shutil
import os
import zipfile


@register_tool(name="remove_directory")
class RemoveDirectoryTool(ToolBase):
    """
    Remove a directory. Raises error if directory not empty and not removed recursively.

    Args:
        directory (str): Path to the directory to remove.

        backup (bool, optional): If True, create a backup (.bak.zip) before removing. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message indicating result. Example:
            - "Directory removed: /path/to/dir"
            - "Error removing directory: <error message>"
    """

    def run(self, directory: str, backup: bool = False) -> str:
        self.report_info(f"🗃️  Removing directory: {directory} ...")
        backup_zip = None
        try:
            if backup and os.path.exists(directory) and os.path.isdir(directory):
                backup_zip = directory.rstrip("/\\") + ".bak.zip"
                with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            abs_path = os.path.join(root, file)
                            rel_path = os.path.relpath(
                                abs_path, os.path.dirname(directory)
                            )
                            zipf.write(abs_path, rel_path)
            if backup:
                shutil.rmtree(directory)
            else:
                os.rmdir(directory)
            self.report_success(f"✅ 1 {pluralize('directory', 1)}")
            msg = f"Directory removed: {directory}"
            if backup_zip:
                msg += f" (backup at {backup_zip})"
            return msg
        except Exception as e:
            self.report_error(f" ❌ Error removing directory: {e}")
            return f"Error removing directory: {e}"
