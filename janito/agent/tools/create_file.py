import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase
from janito.agent.tools.tools_utils import pluralize


@register_tool(name="create_file")
class CreateFileTool(ToolBase):
    """
    Create a new file with the given content. Fails if the file already exists.

    This tool will NOT overwrite existing files. If the file already exists, the operation fails and no changes are made to the file itself.

    Args:
        path (str): Path to the file to create.
        content (str): Content to write to the file.
        backup (bool, optional): If True, create a backup (.bak) before returning an error if the file exists. Defaults to False.
    Returns:
        str: Status message indicating the result. Example:
            - "\u2705 Successfully created the file at ..."
            - "\u2757 Cannot create file: ..."
    """

    def call(self, path: str, content: str, backup: bool = False) -> str:
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        if os.path.exists(path):
            if os.path.isdir(path):
                self.report_error("\u274c Error: is a directory")
                return f"\u274c Cannot create file: '{disp_path}' is an existing directory."
            if backup:
                shutil.copy2(path, path + ".bak")
            self.report_error(f"\u2757 Error: file '{disp_path}' already exists")
            return f"\u2757 Cannot create file: '{disp_path}' already exists."
        # Ensure parent directories exist
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self.report_info(f"\U0001f4dd Creating file: '{disp_path}' ... ")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        self.report_success(f"\u2705 {new_lines} {pluralize('line', new_lines)}")
        return f"\u2705 Successfully created the file at '{disp_path}' ({new_lines} lines)."
