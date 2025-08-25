from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import pluralize
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


@register_local_tool
class ViewFileTool(ToolBase):
    """
    Read lines from a file. You can specify a line range, or read the entire file by simply omitting the from_line and to_line parameters.

    Args:
        path (str): Path to the file to read lines from.
        from_line (int, optional): Starting line number (1-based). Omit to start from the first line.
        to_line (int, optional): Ending line number (1-based). Omit to read to the end of the file.

    To read the full file, just provide path and leave from_line and to_line unset.

    Returns:
        str: File content with a header indicating the file name and line range. Example:
            - "---\nFile: /path/to/file.py | Lines: 1-10 (of 100)\n---\n<lines...>"
            - "---\nFile: /path/to/file.py | All lines (total: 100 (all))\n---\n<all lines...>"
            - "Error reading file: <error message>"
            - "❗ not found"
    """

    permissions = ToolPermissions(read=True)
    tool_name = "view_file"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(self, path: str, from_line: int = None, to_line: int = None) -> str:
        import os
        from janito.tools.tool_utils import display_path
        from janito.tools.path_utils import expand_path

        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(
            tr("📖 View '{disp_path}'", disp_path=disp_path),
            ReportAction.READ,
        )
        try:
            if os.path.isdir(path):
                return self._list_directory(path, disp_path)
            lines = self._read_file_lines(path)
            selected, selected_len, total_lines = self._select_lines(
                lines, from_line, to_line
            )
            self._report_success(selected_len, from_line, to_line, total_lines)
            header = self._format_header(
                disp_path, from_line, to_line, selected_len, total_lines
            )
            return header + "".join(selected)
        except FileNotFoundError as e:
            self.report_warning(tr("❗ not found"))
            return f"Error reading file: {e}"
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error reading file: {error}", error=e)

    def _list_directory(self, path, disp_path):
        import os

        try:
            entries = os.listdir(path)
            entries.sort()
            # Suffix subdirectories with '/'
            formatted_entries = []
            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    formatted_entries.append(entry + "/")
                else:
                    formatted_entries.append(entry)
            header = (
                f"--- view_file: {disp_path} [directory, {len(entries)} entries] ---\n"
            )
            listing = "\n".join(formatted_entries)
            self.report_success(tr("📁 Directory ({count} items)", count=len(entries)))
            return header + listing + "\n"
        except Exception as e:
            self.report_error(tr(" ❌ Error listing directory: {error}", error=e))
            return tr("Error listing directory: {error}", error=e)

    def _read_file_lines(self, path):
        """Read all lines from the file."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
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
            self.report_error(tr("❗ not found"), ReportAction.READ)
            return tr("❗ not found")
        self.report_error(tr(" ❌ Error: {error}", error=e), ReportAction.READ)
        return tr("Error reading file: {error}", error=e)
