import os
from janito.agent.tool_registry import register_tool
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tool_base import ToolBase
from janito.agent.tools.tools_utils import pluralize


@register_tool(name="create_file")
class CreateFileTool(ToolBase):
    """
    Create a new file with the given content. Fails if the file already exists.

    Args:
        path (str): Path to the file to create.
        content (str): Content to write to the file.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully created the file at ..."
            - "❗ Cannot create file: ..."
    """

    def call(self, path: str, content: str) -> str:
        original_path = path
        path = expand_path(path)
        disp_path = display_path(original_path, path)
        if os.path.exists(path):
            if os.path.isdir(path):
                self.report_error("❌ Error: is a directory")
                return f"❌ Cannot create file: '{disp_path}' is an existing directory."
            self.report_error(f"❗ Error: file '{disp_path}' already exists")
            return f"❗ Cannot create file: '{disp_path}' already exists."
        # Ensure parent directories exist
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self.report_info(f"📝 Creating file: '{disp_path}' ... ")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        self.report_success(f"✅ {new_lines} {pluralize('line', new_lines)}")
        return f"✅ Successfully created the file at '{disp_path}' ({new_lines} lines)."
