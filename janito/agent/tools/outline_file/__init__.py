from janito.agent.tool_registry import register_tool
from .python_outline import parse_python_outline
from .markdown_outline import parse_markdown_outline
from .formatting import format_outline_table, format_markdown_outline_table
import os
from janito.agent.tool_base import ToolBase


@register_tool(name="outline_file")
class GetFileOutlineTool(ToolBase):
    """
    Get an outline of a file's structure. Supports Python and Markdown files.

    Args:
        file_path (str): Path to the file to outline.
    """

    def report_info(self, msg):
        pass

    def report_success(self, msg):
        pass

    def report_error(self, msg):
        pass

    def call(self, file_path: str) -> str:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if ext == ".py":
                outline_items = parse_python_outline(lines)
                outline_type = "python"
                table = format_outline_table(outline_items)
                self.report_success(f"✅ {len(outline_items)} items ({outline_type})")
                return f"Outline: {len(outline_items)} items ({outline_type})\n" + table
            elif ext == ".md":
                outline_items = parse_markdown_outline(lines)
                outline_type = "markdown"
                table = format_markdown_outline_table(outline_items)
                self.report_success(f"✅ {len(outline_items)} items ({outline_type})")
                return f"Outline: {len(outline_items)} items ({outline_type})\n" + table
            else:
                outline_type = "default"
                self.report_success(f"✅ {len(lines)} lines ({outline_type})")
                return f"Outline: {len(lines)} lines ({outline_type})\nFile has {len(lines)} lines."
        except Exception as e:
            self.report_error(f"❌ Error reading file: {e}")
            return f"Error reading file: {e}"
