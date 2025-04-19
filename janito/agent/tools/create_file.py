import os
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase
from janito.agent.tools.tools_utils import pluralize

@register_tool(name="create_file")
class CreateFileTool(ToolBase):
    """
    Create a new file or update an existing file with the given content.
    """
    def call(self, path: str, content: str, overwrite: bool = False) -> str:
        """
        Create or update a file with the given content.

        Args:
            path (str): Path to the file to create or update.
            content (str): Content to write to the file.
            overwrite (bool, optional): Whether to overwrite if the file exists. Defaults to False.

        Returns:
            str: Status message indicating the result. Example:
                - "✅ Successfully created the file at ..."
                - "❗ Cannot create file: ..."
        """
        original_path = path
        path = expand_path(path)
        updating = os.path.exists(path) and not os.path.isdir(path)
        disp_path = display_path(original_path, path)
        if os.path.exists(path):
            if os.path.isdir(path):
                self.report_error("❌ Error: is a directory")
                return f"❌ Cannot create file: '{disp_path}' is an existing directory."
            if not overwrite:
                self.report_error(f"❗ Error: file '{disp_path}' exists and overwrite is False")
                return f"❗ Cannot create file: '{disp_path}' already exists and overwrite is False."
        if updating and overwrite:
            self.report_info(f"📝 Updating file: '{disp_path}' ... ")
        else:
            self.report_info(f"📝 Creating file: '{disp_path}' ... ")
        old_lines = None
        if updating and overwrite:
            with open(path, "r", encoding="utf-8") as f:
                old_lines = sum(1 for _ in f)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        new_lines = content.count('\n') + 1 if content else 0
        if old_lines is not None:
            self.report_success(f"✅ {new_lines} {pluralize('line', new_lines)}")
            return f"✅ Successfully updated the file at '{disp_path}' ({old_lines} > {new_lines} lines)."
        self.report_success(f"✅ {new_lines} {pluralize('line', new_lines)}")
        return f"✅ Successfully created the file at '{disp_path}' ({new_lines} lines)."
