from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

@register_tool(name="append_text_to_file")
class AppendTextToFileTool(ToolBase):
    """
    Append the given text to the end of a file.

    Args:
        file_path (str): Path to the file.
        text_to_append (str): Text to append to the file.
    Returns:
        str: Status message.
    """
    def call(self, file_path: str, text_to_append: str) -> str:
        import os
        if not text_to_append:
            self.report_warning("⚠️ Warning: No text provided to append. Operation skipped.")
            return f"Warning: No text provided to append. Operation skipped."
        disp_path = display_path(file_path)
        self.report_info(f"📝 Appending to {disp_path} ({len(text_to_append)} chars)")
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(text_to_append)
            from janito.agent.tools.tools_utils import pluralize
            self.report_success(f"✅ 1 {pluralize('file', 1)}")
            return f"Text appended to {file_path}"
        except Exception as e:
            self.report_error(f"❌ Error: {e}")
            return f"Error appending text: {e}"
# Use display_path for consistent path reporting
from janito.agent.tools.tools_utils import display_path
