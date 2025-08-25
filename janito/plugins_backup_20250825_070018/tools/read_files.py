from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.plugins.tools.decorators import register_core_tool
from janito.tools.tool_utils import pluralize
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


@register_core_tool
class ReadFiles(ToolBase):
    """
    Read all text content from multiple files.

    Args:
        paths (list[str]): List of file paths to read.

    Returns:
        str: Concatenated content of all files, each prefixed by a header with the file name. If a file cannot be read, an error message is included for that file.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "read_files"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="paths")
    def run(self, paths: list[str]) -> str:
        from janito.tools.tool_utils import display_path
        import os
        from janito.tools.path_utils import expand_path

        results = []
        for path in [expand_path(p) for p in paths]:
            disp_path = display_path(path)
            self.report_action(
                tr("📖 Read '{disp_path}'", disp_path=disp_path), ReportAction.READ
            )
            if not os.path.isfile(path):
                self.report_warning(
                    tr("❗ not found: {disp_path}", disp_path=disp_path)
                )
                results.append(f"--- File: {disp_path} (not found) ---\n")
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                results.append(f"--- File: {disp_path} ---\n{content}\n")
                self.report_success(tr("✅ Read {disp_path}", disp_path=disp_path))
            except Exception as e:
                self.report_error(
                    tr(
                        " ❌ Error reading {disp_path}: {error}",
                        disp_path=disp_path,
                        error=e,
                    )
                )
                results.append(
                    f"--- File: {disp_path} (error) ---\nError reading file: {e}\n"
                )
        return "\n".join(results)
