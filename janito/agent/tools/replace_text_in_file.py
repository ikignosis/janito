from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="replace_text_in_file")
class ReplaceTextInFileTool(ToolBase):
    """
    Replace exact occurrences of a given text in a file.

    Args:
        file_path (str): Path to the file to modify.
        search_text (str): The exact text to search for (including indentation).
        replacement_text (str): The text to replace with (including indentation).
        replace_all (bool): If True, replace all occurrences; otherwise, only the first occurrence.
        backup (bool, optional): If True, create a backup (.bak) before replacing. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message. Example:
            - "Text replaced in /path/to/file (backup at /path/to/file.bak)"
            - "No changes made. [Warning: Search text not found in file] Please review the original file."
            - "Error replacing text: <error message>"
    """

    def run(
        self,
        file_path: str,
        search_text: str,
        replacement_text: str,
        replace_all: bool = False,
        backup: bool = False,
    ) -> str:
        from janito.agent.tools_utils.utils import display_path

        disp_path = display_path(file_path)
        action = "(all)" if replace_all else "(unique)"
        search_lines = len(search_text.splitlines())
        replace_lines = len(replacement_text.splitlines())
        if replace_lines == 0:
            info_msg = tr(
                "📝 Replacing in {disp_path} del {search_lines} lines {action}",
                disp_path=disp_path,
                search_lines=search_lines,
                action=action,
            )
        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    _content = f.read()
                _new_content = _content.replace(
                    search_text, replacement_text, -1 if replace_all else 1
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
            info_msg = tr(
                "📝 Replacing in {disp_path} {delta_str} {action}",
                disp_path=disp_path,
                delta_str=delta_str,
                action=action,
            )
        self.report_info(
            info_msg + (" ..." if not info_msg.rstrip().endswith("...") else "")
        )
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            def find_match_lines(content, search_text):
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

            match_lines = find_match_lines(content, search_text)
            if replace_all:
                replaced_count = content.count(search_text)
                new_content = content.replace(search_text, replacement_text)
            else:
                occurrences = content.count(search_text)
                if occurrences > 1:
                    self.report_warning(tr(" ℹ️ No changes made. [not unique]"))
                    warning_detail = tr(
                        "The search text is not unique. Expand your search context with surrounding lines to ensure uniqueness."
                    )
                    return tr(
                        "No changes made. {warning_detail}",
                        warning_detail=warning_detail,
                    )
                replaced_count = 1 if occurrences == 1 else 0
                new_content = content.replace(search_text, replacement_text, 1)
            import shutil

            backup_path = file_path + ".bak"
            if backup and new_content != content:
                shutil.copy2(file_path, backup_path)
            if new_content != content:
                with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(new_content)
                file_changed = True
            else:
                file_changed = False
            warning = ""
            if replaced_count == 0:
                warning = tr(" [Warning: Search text not found in file]")
            if not file_changed:
                self.report_warning(tr(" ℹ️ No changes made. [not found]"))
                concise_warning = tr(
                    "The search text was not found. Expand your search context with surrounding lines if needed."
                )
                return tr(
                    "No changes made. {concise_warning}",
                    concise_warning=concise_warning,
                )
            if match_lines:
                lines_str = ", ".join(str(line_no) for line_no in match_lines)
                self.report_success(
                    tr(" ✅ replaced at {lines_str}", lines_str=lines_str)
                )
            else:
                self.report_success(tr(" ✅ replaced (lines unknown)"))

            def leading_ws(line):
                import re

                m = re.match(r"^\s*", line)
                return m.group(0) if m else ""

            search_indent = (
                leading_ws(search_text.splitlines()[0])
                if search_text.splitlines()
                else ""
            )
            replace_indent = (
                leading_ws(replacement_text.splitlines()[0])
                if replacement_text.splitlines()
                else ""
            )
            indent_warning = ""
            if search_indent != replace_indent:
                indent_warning = tr(
                    " [Warning: Indentation mismatch between search and replacement text: '{search_indent}' vs '{replace_indent}']",
                    search_indent=search_indent,
                    replace_indent=replace_indent,
                )
            total_lines_before = content.count("\n") + 1
            total_lines_after = new_content.count("\n") + 1
            line_delta = total_lines_after - total_lines_before
            line_delta_str = (
                f" (+{line_delta} lines)"
                if line_delta > 0
                else (
                    f" ({line_delta} lines)"
                    if line_delta < 0
                    else " (no net line change)"
                )
            )
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
            if "warning_detail" in locals():
                return tr(
                    "Text replaced in {file_path}{warning}{indent_warning} (backup at {backup_path})\n{warning_detail}",
                    file_path=file_path,
                    warning=warning,
                    indent_warning=indent_warning,
                    backup_path=backup_path,
                    warning_detail=warning_detail,
                )
            return tr(
                "Text replaced in {file_path}{warning}{indent_warning} (backup at {backup_path}). {match_info}{details}",
                file_path=file_path,
                warning=warning,
                indent_warning=indent_warning,
                backup_path=backup_path,
                match_info=match_info,
                details=details,
            )
        except Exception as e:
            self.report_error(tr(" ❌ Error"))
            return tr("Error replacing text: {error}", error=e)
