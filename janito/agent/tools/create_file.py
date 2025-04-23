import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase


@register_tool(name="create_file")
class CreateFileTool(ToolBase):
    """
    Create a new file with the given content, or overwrite if specified.

    Args:
        path (str): Path to the file to create or overwrite.
        content (str): Content to write to the file.
        overwrite (bool, optional): If True, overwrite the file if it exists. Defaults to False.
        backup (bool, optional): If True, create a backup (.bak) before overwriting. Defaults to True.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully created the file at ..."
    """

    def call(self, path, content, overwrite=False, backup=True) -> str:
        original_path = path
        expanded_path = expand_path(path)
        disp_path = display_path(original_path, expanded_path)
        path = expanded_path
        backup_path = None
        if os.path.exists(path):
            if not overwrite:
                return f"⚠️ File already exists at '{disp_path}'. Use overwrite=True to overwrite."
            backup_info = ""
            if backup:
                backup_path = path + ".bak"
                shutil.copy2(path, backup_path)
                # Only show the filename for the .bak created message
                backup_filename = os.path.basename(backup_path)
                backup_info = f" {backup_filename} created"
            self.report_info(f"📝 Updating file: '{disp_path}'..." + backup_info)
            mode = "w"
            updated = True
        else:
            # Ensure parent directories exist
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self.report_info(f"📝 Creating file: '{disp_path}' ... ")
            mode = "w"
            updated = False
        with open(path, mode, encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        if updated:
            self.report_success(f"✅ ({new_lines} lines).")
            msg = f"✅ Updated file ({new_lines} lines)."
            if backup_path:
                backup_filename = os.path.basename(backup_path)
                msg += f" {backup_filename} created"
            return msg
        else:
            self.report_success(f"✅ ({new_lines} lines).")
            return f"✅ Created file ({new_lines} lines)."
