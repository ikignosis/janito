from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import pluralize
from janito.i18n import tr


@register_tool(name="get_lines")
class GetLinesTool(ToolBase):
    """
    Read lines from a file. You can specify a line range, or read the entire file by simply omitting the from_line and to_line parameters.

    Args:
        file_path (str): Path to the file to read lines from.
        from_line (int, optional): Starting line number (1-based). Omit to start from the first line.
        to_line (int, optional): Ending line number (1-based). Omit to read to the end of the file.

    To read the full file, just provide file_path and leave from_line and to_line unset.

    Returns:
        str: File content with a header indicating the file name and line range. Example:
            - "---\nFile: /path/to/file.py | Lines: 1-10 (of 100)\n---\n<lines...>"
            - "---\nFile: /path/to/file.py | All lines (total: 100 (all))\n---\n<all lines...>"
            - "Error reading file: <error message>"
            - "❗ not found"
    """

    def run(self, file_path: str, from_line: int = None, to_line: int = None) -> str:
        from janito.agent.tools_utils.utils import display_path

        disp_path = display_path(file_path)
        self._report_read_info(disp_path, from_line, to_line)
        try:
            lines = self._read_file_lines(file_path)
            selected, selected_len, total_lines = self._select_lines(
                lines, from_line, to_line
            )
            self._report_success(selected_len, from_line, to_line, total_lines)
            header = self._format_header(
                disp_path, from_line, to_line, selected_len, total_lines
            )
            return header + "".join(selected)
        except Exception as e:
            return self._handle_read_error(e)

    def _report_read_info(self, disp_path, from_line, to_line):
        """Report the info message for reading lines."""
        if from_line and to_line:
            self.report_info(
                ActionType.READ,
                tr(
                    "📖 Read file '{disp_path}' {from_line}-{to_line}",
                    disp_path=disp_path,
                    from_line=from_line,
                    to_line=to_line,
                ),
            )
        else:
            self.report_info(
                ActionType.READ,
                tr("📖 Read file '{disp_path}'", disp_path=disp_path),
            )

    def _read_file_lines(self, file_path):
        """Read all lines from the file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()

    def _select_lines(self, lines, from_line, to_line):
        """Select the requested lines and return them with their count and total lines."""
        selected = lines[
            (from_line - 1 if from_line else 0) : (to_line if to_line else None)
        ]
        selected_len = len(selected)
        total_lines = len(lines)
        return selected, selected_len, total_lines

    def _report_success(self, selected_len, from_line, to_line, total_lines):
        """Report the success message after reading lines."""
        if from_line and to_line:
            requested = to_line - from_line + 1
            at_end = to_line >= total_lines or selected_len < requested
            if at_end:
                self.report_success(
                    tr(
                        " ✅ {selected_len} {line_word} (end)",
                        selected_len=selected_len,
                        line_word=pluralize("line", selected_len),
                    )
                )
            elif to_line < total_lines:
                self.report_success(
                    tr(
                        " ✅ {selected_len} {line_word} ({remaining} to end)",
                        selected_len=selected_len,
                        line_word=pluralize("line", selected_len),
                        remaining=total_lines - to_line,
                    )
                )
        else:
            self.report_success(
                tr(
                    " ✅ {selected_len} {line_word} (all)",
                    selected_len=selected_len,
                    line_word=pluralize("line", selected_len),
                )
            )

    def _format_header(self, disp_path, from_line, to_line, selected_len, total_lines):
        """Format the header for the output."""
        if from_line and to_line:
            requested = to_line - from_line + 1
            at_end = selected_len < requested or to_line >= total_lines
            if at_end:
                return tr(
                    "---\n{disp_path} {from_line}-{to_line} (end)\n---\n",
                    disp_path=disp_path,
                    from_line=from_line,
                    to_line=to_line,
                )
            else:
                return tr(
                    "---\n{disp_path} {from_line}-{to_line} (of {total_lines})\n---\n",
                    disp_path=disp_path,
                    from_line=from_line,
                    to_line=to_line,
                    total_lines=total_lines,
                )
        elif from_line:
            return tr(
                "---\n{disp_path} {from_line}-END (of {total_lines})\n---\n",
                disp_path=disp_path,
                from_line=from_line,
                total_lines=total_lines,
            )
        else:
            return tr(
                "---\n{disp_path} All lines (total: {total_lines} (all))\n---\n",
                disp_path=disp_path,
                total_lines=total_lines,
            )

    def _handle_read_error(self, e):
        """Handle file read errors and report appropriately."""
        if isinstance(e, FileNotFoundError):
            self.report_error(tr("❗ not found"))
            return tr("❗ not found")
        self.report_error(tr(" ❌ Error: {error}", error=e))
        return tr("Error reading file: {error}", error=e)
