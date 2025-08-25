from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.i18n import tr
import shutil
import re
from janito.tools.adapters.local.validate_file_syntax.core import validate_file_syntax


@register_local_tool
class ReplaceTextInFileTool(ToolBase):
    """
    Replace exact occurrences of a given text in a file.

    Note:
        To avoid syntax errors, ensure your replacement text is pre-indented as needed, matching the indentation of the
        search text in its original location.

    Args:
        path (str): Path to the file to modify.
        search_text (str): The exact text to search for (including indentation).
        replacement_text (str): The text to replace with (including indentation).
        replace_all (bool): If True, replace all occurrences; otherwise, only the first occurrence.
        backup (bool, optional): Deprecated. No backups are created anymore and this flag is ignored. Defaults to False.
    Returns:
        str: Status message. Example:
            - "Text replaced in /path/to/file"
            - "No changes made. [Warning: Search text not found in file] Please review the original file."
            - "Error replacing text: <error message>"
    """

    permissions = ToolPermissions(read=True, write=True)
    tool_name = "replace_text_in_file"

    def run(
        self,
        path: str,
        search_text: str,
        replacement_text: str,
        replace_all: bool = False,
        backup: bool = False,
    ) -> str:
        from janito.tools.tool_utils import display_path

        disp_path = display_path(path)
        action = "(all)" if replace_all else ""
        search_lines = len(search_text.splitlines())
        replace_lines = len(replacement_text.splitlines())
        info_msg = self._format_info_msg(
            disp_path,
            search_lines,
            replace_lines,
            action,
            search_text,
            replacement_text,
            path,
        )
        self.report_action(info_msg, ReportAction.CREATE)
        try:
            content = self._read_file_content(path)
            match_lines = self._find_match_lines(content, search_text)
            occurrences = content.count(search_text)
            replaced_count, new_content = self._replace_content(
                content, search_text, replacement_text, replace_all, occurrences
            )
            file_changed = new_content != content
            backup_path = None
            validation_result = ""
            if file_changed:
                self._write_file_content(path, new_content)
                # Perform syntax validation and append result
                validation_result = validate_file_syntax(path)
            warning, concise_warning = self._handle_warnings(
                replaced_count, file_changed, occurrences
            )

            if concise_warning:
                return concise_warning
            self._report_success(match_lines)
            line_delta_str = self._get_line_delta_str(content, new_content)
            match_info, details = self._format_match_details(
                replaced_count,
                match_lines,
                search_lines,
                replace_lines,
                line_delta_str,
                replace_all,
            )
            return self._format_final_msg(path, warning, match_info, details) + (
                f"\n{validation_result}" if validation_result else ""
            )
        except Exception as e:
            self.report_error(tr(" ❌ Error"), ReportAction.UPDATE)
            return tr("Error replacing text: {error}", error=e)

    def _read_file_content(self, path):
        """Read the entire content of the file."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _find_match_lines(self, content, search_text):
        """Find all line numbers where search_text occurs in content."""
        lines = content.splitlines(keepends=True)
        joined = "".join(lines)
        match_lines = []
        idx = 0
        while True:
            idx = joined.find(search_text, idx)
            if idx == -1:
                break
            upto = joined[:idx]
            line_no = upto.count("\n") + 1
            match_lines.append(line_no)
            idx += 1 if not search_text else len(search_text)
        return match_lines

    def _replace_content(
        self, content, search_text, replacement_text, replace_all, occurrences
    ):
        """Replace occurrences of search_text with replacement_text in content."""
        if replace_all:
            replaced_count = content.count(search_text)
            new_content = content.replace(search_text, replacement_text)
        else:
            if occurrences > 1:
                return 0, content  # No changes made, not unique
            replaced_count = 1 if occurrences == 1 else 0
            new_content = content.replace(search_text, replacement_text, 1)
        return replaced_count, new_content

    def _backup_file(self, path, backup_path):
        """Create a backup of the file."""
        shutil.copy2(path, backup_path)

    def _write_file_content(self, path, content):
        """Write content to the file."""
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

    def _handle_warnings(self, replaced_count, file_changed, occurrences):
        """Handle and return warnings and concise warnings if needed."""
        warning = ""
        concise_warning = None
        if replaced_count == 0:
            warning = tr(" [Warning: Search text not found in file]")
        if not file_changed:
            self.report_warning(
                tr(" ℹ️  No changes made. (not found)"), ReportAction.CREATE
            )
            concise_warning = tr(
                "No changes made. The search text was not found. Expand your search context with surrounding lines if needed."
            )
        if occurrences > 1 and replaced_count == 0:
            self.report_warning(
                tr(" ℹ️  No changes made. (not unique)"), ReportAction.CREATE
            )
            concise_warning = tr(
                "No changes made. The search text is not unique. Expand your search context with surrounding lines to ensure uniqueness."
            )
        return warning, concise_warning

    def _report_success(self, match_lines):
        """Report success with line numbers where replacements occurred."""
        if match_lines:
            lines_str = ", ".join(str(line_no) for line_no in match_lines)
            self.report_success(
                tr(" ✅ replaced at {lines_str}", lines_str=lines_str),
                ReportAction.CREATE,
            )
        else:
            self.report_success(tr(" ✅ replaced (lines unknown)"), ReportAction.CREATE)

    def _get_line_delta_str(self, content, new_content):
        """Return a string describing the net line change after replacement."""
        total_lines_before = content.count("\n") + 1
        total_lines_after = new_content.count("\n") + 1
        line_delta = total_lines_after - total_lines_before
        if line_delta > 0:
            return f" (+{line_delta} lines)"
        elif line_delta < 0:
            return f" ({line_delta} lines)"
        else:
            return " (no net line change)"

    def _format_info_msg(
        self,
        disp_path,
        search_lines,
        replace_lines,
        action,
        search_text,
        replacement_text,
        path,
    ):
        """Format the info message for the operation."""
        if replace_lines == 0:
            return tr(
                "📝 Replace in {disp_path} del {search_lines} lines {action}",
                disp_path=disp_path,
                search_lines=search_lines,
                action=action,
            )
        else:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    _content = f.read()
                _new_content = _content.replace(
                    search_text, replacement_text, -1 if action else 1
                )
                _total_lines_before = _content.count("\n") + 1
                _total_lines_after = _new_content.count("\n") + 1
                _line_delta = _total_lines_after - _total_lines_before
            except Exception:
                _line_delta = replace_lines - search_lines
            if _line_delta > 0:
                delta_str = f"+{_line_delta} lines"
            elif _line_delta < 0:
                delta_str = f"{_line_delta} lines"
            else:
                delta_str = "+0"
            return tr(
                "📝 Replace in {disp_path} {delta_str} {action}",
                disp_path=disp_path,
                delta_str=delta_str,
                action=action,
            )

    def _format_match_details(
        self,
        replaced_count,
        match_lines,
        search_lines,
        replace_lines,
        line_delta_str,
        replace_all,
    ):
        """Format match info and details for the final message."""
        if replaced_count > 0:
            if replace_all:
                match_info = tr(
                    "Matches found at lines: {lines}. ",
                    lines=", ".join(str(line) for line in match_lines),
                )
            else:
                match_info = (
                    tr("Match found at line {line}. ", line=match_lines[0])
                    if match_lines
                    else ""
                )
            details = tr(
                "Replaced {replaced_count} occurrence(s) at above line(s): {search_lines} lines replaced with {replace_lines} lines each.{line_delta_str}",
                replaced_count=replaced_count,
                search_lines=search_lines,
                replace_lines=replace_lines,
                line_delta_str=line_delta_str,
            )
        else:
            match_info = ""
            details = ""
        return match_info, details

    def _format_final_msg(self, path, warning, match_info, details):
        """Format the final status message."""
        return tr(
            "Text replaced in {path}{warning}. {match_info}{details}",
            path=path,
            warning=warning,
            match_info=match_info,
            details=details,
        )
