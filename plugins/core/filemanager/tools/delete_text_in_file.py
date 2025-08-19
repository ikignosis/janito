from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.i18n import tr
import shutil
from janito.tools.adapters.local.validate_file_syntax.core import validate_file_syntax


@register_local_tool
class DeleteTextInFileTool(ToolBase):
    """
    Delete all occurrences of text between start_marker and end_marker (inclusive) in a file, using exact string markers.

    Args:
        path (str): Path to the file to modify.
        start_marker (str): The starting delimiter string.
        end_marker (str): The ending delimiter string.

    Returns:
        str: Status message indicating the result.
    """

    permissions = ToolPermissions(read=True, write=True)
    tool_name = "delete_text_in_file"

    def run(
        self,
        path: str,
        start_marker: str,
        end_marker: str,
        backup: bool = False,
    ) -> str:
        from janito.tools.tool_utils import display_path

        disp_path = display_path(path)
        info_msg = tr(
            "📝 Delete text in {disp_path} between markers: '{start_marker}' ... '{end_marker}'",
            disp_path=disp_path,
            start_marker=start_marker,
            end_marker=end_marker,
        )
        self.report_action(info_msg, ReportAction.CREATE)
        try:
            content = self._read_file_content(path)
            occurrences, match_lines = self._find_marker_blocks(
                content, start_marker, end_marker
            )
            if occurrences == 0:
                self.report_warning(
                    tr(" ℹ️ No blocks found between markers."), ReportAction.CREATE
                )
                return tr(
                    "No blocks found between markers in {path}.",
                    path=path,
                )

            new_content, deleted_blocks = self._delete_blocks(
                content, start_marker, end_marker
            )
            self._write_file_content(path, new_content)
            validation_result = validate_file_syntax(path)
            self._report_success(match_lines)
            return tr(
                "Deleted {count} block(s) between markers in {path}. ",
                count=deleted_blocks,
                path=path,
            ) + (f"\n{validation_result}" if validation_result else "")
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e), ReportAction.REPLACE)
            return tr("Error deleting text: {error}", error=e)

    def _read_file_content(self, path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _find_marker_blocks(self, content, start_marker, end_marker):
        """Find all blocks between start_marker and end_marker, return count and starting line numbers."""
        lines = content.splitlines(keepends=True)
        joined = "".join(lines)
        match_lines = []
        idx = 0
        occurrences = 0
        while True:
            start_idx = joined.find(start_marker, idx)
            if start_idx == -1:
                break
            end_idx = joined.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                break
            upto = joined[:start_idx]
            line_no = upto.count("\n") + 1
            match_lines.append(line_no)
            idx = end_idx + len(end_marker)
            occurrences += 1
        return occurrences, match_lines

    def _delete_blocks(self, content, start_marker, end_marker):
        """Delete all blocks between start_marker and end_marker (inclusive)."""
        count = 0
        new_content = content
        while True:
            start_idx = new_content.find(start_marker)
            if start_idx == -1:
                break
            end_idx = new_content.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                break
            new_content = (
                new_content[:start_idx] + new_content[end_idx + len(end_marker) :]
            )
            count += 1
        return new_content, count

    def _backup_file(self, path, backup_path):
        shutil.copy2(path, backup_path)

    def _write_file_content(self, path, content):
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

    def _report_success(self, match_lines):
        if match_lines:
            lines_str = ", ".join(str(line_no) for line_no in match_lines)
            self.report_success(
                tr(
                    " ✅ deleted block(s) starting at line(s): {lines_str}",
                    lines_str=lines_str,
                ),
                ReportAction.CREATE,
            )
        else:
            self.report_success(
                tr(" ✅ deleted block(s) (lines unknown)"), ReportAction.CREATE
            )
