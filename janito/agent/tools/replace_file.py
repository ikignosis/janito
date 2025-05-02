import os
import shutil
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import display_path
from janito.agent.tool_base import ToolBase
from janito.i18n import tr

from janito.agent.tools.validate_file_syntax.core import validate_file_syntax


@register_tool(name="replace_file")
class ReplaceFileTool(ToolBase):
    """
    Replace the entire content of an existing file. Fails if the file does not exist.
    Args:
        file_path (str): Path to the file to replace content.
        content (str): The full new content to write to the file. You must provide the complete content as it will fully overwrite the existing file—do not use placeholders for original content.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully replaced the file at ..."
    """

    def run(self, file_path: str, content: str) -> str:
        from janito.agent.tool_use_tracker import ToolUseTracker

        expanded_file_path = file_path  # Using file_path as is
        disp_path = display_path(expanded_file_path)
        file_path = expanded_file_path
        if not os.path.exists(file_path):
            return tr(
                "❗ Cannot replace: file does not exist at '{disp_path}'.",
                disp_path=disp_path,
            )
        # Check previous operation
        tracker = ToolUseTracker()
        if not tracker.last_operation_is_full_read_or_replace(file_path):
            self.report_warning("missing full view")
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    current_content = f.read()
            except Exception as e:
                current_content = f"[Error reading file: {e}]"
            return (
                "⚠️ [missing full view] You must fully view or replace the file before updating.\n"
                f"--- Current content of {disp_path} ---\n"
                f"{current_content}"
            )
        self.report_info(
            tr("📝 Replacing file: '{disp_path}' ...", disp_path=disp_path)
        )
        backup_path = file_path + ".bak"
        shutil.copy2(file_path, backup_path)
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        self.report_success(tr("✅ ({new_lines} lines).", new_lines=new_lines))
        msg = tr(
            "✅ Replaced file ({new_lines} lines, backup at {backup_path}).",
            new_lines=new_lines,
            backup_path=backup_path,
        )
        # Perform syntax validation and append result
        validation_result = validate_file_syntax(file_path)
        return msg + f"\n{validation_result}"
