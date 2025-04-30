from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import display_path


@register_tool(name="show_edit_url")
class ShowEditUrlTool(ToolBase):
    """
    Present the edit URL for a file to the user (simulated).

    Args:
        file_path (str): The path to the file to edit.
    Returns:
        str: Confirmation message that the URL was presented.
    """

    def run(self, file_path: str) -> str:
        disp_path = display_path(file_path)
        self.report_info(f"🔗 Presenting edit URL for: {disp_path}\n")
        return "The url was presented to the user"
