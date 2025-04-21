import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase


@register_tool(name="replace_file")
class ReplaceFileTool(ToolBase):
    """
    Overwrite (replace) a file with the given content. Creates the file if it does not exist.

    Args:
        path (str): Path to the file to overwrite or create.
        content (str): Content to write to the file.
        backup (bool, optional): If True, create a backup (.bak) before replacing if the file exists. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message indicating the result. Example:
            - "\u2705 Successfully replaced the file at ..."
            - "\u2705 Successfully created the file at ..."
    """

    def call(self, path: str, content: str, backup: bool = False) -> str:
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        updating = os.path.exists(path) and not os.path.isdir(path)
        if os.path.exists(path) and os.path.isdir(path):
            self.report_error("\u274c Error: is a directory")
            return (
                f"\u274c Cannot replace file: '{disp_path}' is an existing directory."
            )
        # Ensure parent directories exist
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if backup and os.path.exists(path) and not os.path.isdir(path):
            shutil.copy2(path, path + ".bak")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        if updating:
            self.report_success(
                f"\u2705 Successfully replaced the file at '{disp_path}' ({new_lines} lines)."
            )
            return f"\u2705 Successfully replaced the file at '{disp_path}' ({new_lines} lines)."
        else:
            self.report_success(
                f"\u2705 Successfully created the file at '{disp_path}' ({new_lines} lines)."
            )
            return f"\u2705 Successfully created the file at '{disp_path}' ({new_lines} lines)."
