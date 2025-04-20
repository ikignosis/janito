from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize


@register_tool(name="get_file_outline")
class GetFileOutlineTool(ToolBase):
    """
    Get an outline of a file's structure.

    Args:
        file_path (str): Path to the file.
    Returns:
        str: Outline of the file's structure, starting with a summary line. Example:
            - "Outline: 5 items\nclass MyClass:\ndef my_function():\n..."
            - "Error reading file: <error message>"
    """

    def call(self, file_path: str) -> str:
        from janito.agent.tools.tools_utils import display_path

        disp_path = display_path(file_path)
        self.report_info(f"📄 Getting outline for: {disp_path}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            outline = [line.strip() for line in lines if line.strip()]
            num_items = len(outline)

            self.report_success(f" ✅ {num_items} {pluralize('item', num_items)}")
            return f"Outline: {num_items} items\n" + "\n".join(outline)
        except Exception as e:
            self.report_error(f" ❌ Error reading file: {e}")
            return f"Error reading file: {e}"
