from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler

from janito.agent.tools.rich_utils import print_info, print_success, print_error

class GetFileOutlineTool(ToolBase):
    """Get an outline of a file's structure."""
    def call(self, file_path: str) -> str:
        print_info(f"📄 Getting outline for: {file_path}")
        self.update_progress(f"Getting outline for: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            outline = [line.strip() for line in lines if line.strip()]
            print_success(f"\u2705 Outline generated for {file_path}")
            return '\n'.join(outline)
        except Exception as e:
            print_error(f"\u274c Error reading file: {e}")
            return f"Error reading file: {e}"

ToolHandler.register_tool(GetFileOutlineTool, name="get_file_outline")
