import os
import shutil
from janito.agent.tool_registry import register_tool

# from janito.agent.tools_utils.expand_path import expand_path
from janito.agent.tools_utils.utils import display_path
from janito.agent.tool_base import ToolBase
from janito.i18n import tr


@register_tool(name="create_file")
class CreateFileTool(ToolBase):
    """
    Create a new file with the given content, or overwrite if specified.
    Args:
        file_path (str): Path to the file to create or overwrite.
        content (str): Content to write to the file.
        overwrite (bool, optional): If True, overwrite the file if it exists. Defaults to False.
            CRITICAL: If you use overwrite=True, you MUST provide the full content for the file. Using placeholders or partial content will result in file corruption. Before overwriting, read the full original file.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully created the file at ..."
    """

    def run(self, file_path: str, content: str, overwrite: bool = False) -> str:
        expanded_file_path = file_path  # Using file_path as is
        disp_path = display_path(expanded_file_path)
        file_path = expanded_file_path
        backup_path = None
        if os.path.exists(file_path):
            if not overwrite:
                return tr(
                    "⚠️ File already exists at '{disp_path}'. Use overwrite=True to overwrite.",
                    disp_path=disp_path,
                )
            # Check ToolUseTracker for full read before overwrite
            try:
                from janito.agent.tool_use_tracker import ToolUseTracker

                tracker = ToolUseTracker()
                if not tracker.file_fully_read(file_path):
                    self.report_error(
                        "❌ Refusing to overwrite file: full file has not been read with get_lines."
                    )
                    return tr(
                        "❌ Refusing to overwrite file: full file has not been read with get_lines."
                    )
            except Exception as e:
                self.report_error(f"[ToolUseTracker] Error: {e}")
                return tr("[ToolUseTracker] Error: {e}")
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)
            self.report_info(
                tr("📝 Updating file: '{disp_path}' ...", disp_path=disp_path)
            )
            mode = "w"
            updated = True
        else:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self.report_info(
                tr("📝 Creating file: '{disp_path}' ...", disp_path=disp_path)
            )
            mode = "w"
            updated = False
        with open(file_path, mode, encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        if updated:
            self.report_success(tr("✅ ({new_lines} lines).", new_lines=new_lines))
            msg = tr(
                "✅ Updated file ({new_lines} lines, backup at {backup_path}).",
                new_lines=new_lines,
                backup_path=backup_path,
            )
            return msg
        else:
            self.report_success(tr("✅ ({new_lines} lines).", new_lines=new_lines))
            return tr("✅ Created file ({new_lines} lines).", new_lines=new_lines)
