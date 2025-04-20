from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import display_path, pluralize


@register_tool(name="append_text_to_file")
class AppendTextToFileTool(ToolBase):
    """
    Append the given text to the end of a file.
    """

    def call(self, file_path: str, text_to_append: str) -> str:
        """
        Append the given text to the end of a file.

        Append the given text to the end of a file.

        Args:
            file_path (str): Path to the file where text will be appended.
            text_to_append (str): The text content to append to the file.
        Returns:
            str: Status message. Example formats:
                - "Appended 3 lines to /path/to/file.txt"
                - "Warning: No text provided to append. Operation skipped."
                - "Error appending text: <error message>"
        """
        if not text_to_append:
            self.report_warning(
                "⚠️ Warning: No text provided to append. Operation skipped."
            )
            return "Warning: No text provided to append. Operation skipped."
        disp_path = display_path(file_path)
        self.report_info(f"📝 Appending to {disp_path} ({len(text_to_append)} chars)")
        try:
            with open(file_path, "a", encoding="utf-8", errors="replace") as f:
                f.write(text_to_append)

            num_lines = text_to_append.count("\n") + (1 if text_to_append else 0)
            self.report_success(
                f"✅ {num_lines} {pluralize('line', num_lines)} appended"
            )
            return f"Appended {num_lines} {pluralize('line', num_lines)} to {file_path}"
        except Exception as e:
            self.report_error(f"❌ Error: {e}")
            return f"Error appending text: {e}"
