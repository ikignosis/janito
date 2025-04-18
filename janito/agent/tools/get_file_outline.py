from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool




@register_tool(name="get_file_outline")
class GetFileOutlineTool(ToolBase):
    """Get an outline of a file's structure."""
    def call(self, file_path: str) -> str:
        self.report_info(f"📄 Getting outline for: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            outline = [line.strip() for line in lines if line.strip()]
            num_items = len(outline)
            self.report_success(f"✅ {num_items} items")
            return f"Outline: {num_items} items\n" + '\n'.join(outline)
        except Exception as e:
            self.report_error(f"❌ Error reading file: {e}")
            return f"Error reading file: {e}"


