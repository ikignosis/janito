import os
from janito.tools.path_utils import expand_path
from janito.tools.adapters.local.adapter import register_local_tool

from janito.tools.tool_utils import display_path
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops

from janito.tools.adapters.local.validate_file_syntax.core import validate_file_syntax


@register_local_tool
class CreateFileTool(ToolBase):
    """
    Create a new file with the given content.

    Args:
        path (str): Path to the file to create.
        content (str): Content to write to the file.
        overwrite (bool, optional): Overwrite existing file if True. Default: False. Recommended only after reading the file to be overwritten.
    Returns:
        str: Status message indicating the result. Example:
            - "✅ Successfully created the file at ..."

    Note: Syntax validation is automatically performed after this operation.

    Security: This tool includes loop protection to prevent excessive file creation operations.
    Protection: Prevents repeated create calls for the same file path within a short window (1 allowed per 10 seconds).
    """

    permissions = ToolPermissions(write=True)
    tool_name = "create_file"

    @protect_against_loops(max_calls=1, time_window=10.0, key_field="path")
    def run(self, path: str, content: str, overwrite: bool = False) -> str:
        path = expand_path(path)
        disp_path = display_path(path)
        if os.path.exists(path) and not overwrite:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    existing_content = f.read()
            except Exception as e:
                existing_content = f"[Error reading file: {e}]"
            return tr(
                "❗ Cannot create file: file already exists at '{disp_path}'.\n--- Current file content ---\n{existing_content}",
                disp_path=disp_path,
                existing_content=existing_content,
            )
        # Determine if we are overwriting an existing file
        is_overwrite = os.path.exists(path) and overwrite
        if is_overwrite:
            # Overwrite branch: log only overwrite warning (no create message)
            self.report_action(
                tr("⚠️  Overwriting file '{disp_path}'", disp_path=disp_path),
                ReportAction.CREATE,
            )
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not is_overwrite:
            # Create branch: log file creation message
            self.report_action(
                tr("📝 Create file '{disp_path}' ...", disp_path=disp_path),
                ReportAction.CREATE,
            )
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        new_lines = content.count("\n") + 1 if content else 0
        self.report_success(
            tr("✅ {new_lines} lines", new_lines=new_lines), ReportAction.CREATE
        )
        # Perform syntax validation and append result
        validation_result = validate_file_syntax(path)
        if is_overwrite:
            # Overwrite branch: return minimal overwrite info to user
            return (
                tr("✅ {new_lines} lines", new_lines=new_lines)
                + f"\n{validation_result}"
            )
        else:
            # Create branch: return detailed create success to user
            return (
                tr("✅ Created file {new_lines} lines.", new_lines=new_lines)
                + f"\n{validation_result}"
            )
