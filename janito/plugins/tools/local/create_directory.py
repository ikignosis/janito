from janito.plugins.tools.local.adapter import register_local_tool

from janito.tools.tool_utils import display_path
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
import os
from janito.tools.path_utils import expand_path
from pathlib import Path


@register_local_tool
class CreateDirectoryTool(ToolBase):
    """
    Create a new directory at the specified path.
    Args:
        path (str): Path for the new directory.
    Returns:
        str: Status message indicating the result. Example:
            - "5c5 Successfully created the directory at ..."
            - "5d7 Cannot create directory: ..."
    """

    permissions = ToolPermissions(write=True)
    tool_name = "create_directory"

    def run(self, path: str) -> str:
        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(
            tr("📁 Create directory '{disp_path}' ...", disp_path=disp_path),
            ReportAction.CREATE,
        )
        try:
            if os.path.exists(path):
                if not os.path.isdir(path):
                    self.report_error(
                        tr(
                            "❌ Path '{disp_path}' exists and is not a directory.",
                            disp_path=disp_path,
                        )
                    )
                    return tr(
                        "❌ Path '{disp_path}' exists and is not a directory.",
                        disp_path=disp_path,
                    )
                # Generate content summary
                content_summary = self._get_directory_summary(path)
                self.report_error(
                    tr(
                        "❗ Directory '{disp_path}' already exists.",
                        disp_path=disp_path,
                    )
                )
                return tr(
                    "❗ Cannot create directory: '{disp_path}' already exists.\n{summary}",
                    disp_path=disp_path,
                    summary=content_summary,
                )
            os.makedirs(path, exist_ok=True)
            self.report_success(tr("✅ Directory created"))
            return tr(
                "✅ Successfully created the directory at '{disp_path}'.",
                disp_path=disp_path,
            )
        except Exception as e:
            self.report_error(
                tr(
                    "❌ Error creating directory '{disp_path}': {error}",
                    disp_path=disp_path,
                    error=e,
                )
            )
            return tr("❌ Cannot create directory: {error}", error=e)

    def _get_directory_summary(self, path: str) -> str:
        """Generate a summary of directory contents."""
        try:
            path_obj = Path(path)
            if not path_obj.exists() or not path_obj.is_dir():
                return ""
            
            items = list(path_obj.iterdir())
            if not items:
                return "Directory is empty."
            
            # Count files and directories
            file_count = sum(1 for item in items if item.is_file())
            dir_count = sum(1 for item in items if item.is_dir())
            
            summary_parts = []
            if file_count > 0:
                summary_parts.append(f"{file_count} file{'s' if file_count != 1 else ''}")
            if dir_count > 0:
                summary_parts.append(f"{dir_count} subdirector{'y' if dir_count == 1 else 'ies'}")
            
            # Show first few items as examples
            examples = []
            for item in sorted(items)[:3]:  # Show up to 3 items
                if item.is_dir():
                    examples.append(f"📁 {item.name}")
                else:
                    examples.append(f"📄 {item.name}")
            
            result = f"Contains: {', '.join(summary_parts)}."
            if examples:
                result += f"\nExamples: {', '.join(examples)}"
                if len(items) > 3:
                    result += f" (and {len(items) - 3} more)"
            
            return result
        except Exception:
            return "Unable to read directory contents."