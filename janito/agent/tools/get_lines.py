from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool



@register_tool(name="get_lines")
class GetLinesTool(ToolBase):
    """Read lines from a file. Returns specific lines if a range is provided, or the entire file if no range is given."""
    def call(self, file_path: str, from_line: int=None, to_line: int=None) -> str:
        """
        Get specific lines from a file.

        Args:
            file_path (str): Path to the file to read lines from.
            from_line (int, optional): Starting line number (1-based). If None, starts from the first line.
            to_line (int, optional): Ending line number (1-based). If None, reads to the end of the file. If both are None, the entire file is returned.

        Returns:
            str: File content with a header indicating the file name and line range. Example:
                - "---\nFile: /path/to/file.py | Lines: 1-10 (of 100)\n---\n<lines...>"
                - "---\nFile: /path/to/file.py | All lines (total: 100)\n---\n<all lines...>"
                - "Error reading file: <error message>"
                - "❗ not found"
        """
        from janito.agent.tools.tools_utils import display_path
        disp_path = display_path(file_path)
        if from_line and to_line:
            self.report_info(f"📄 Reading {disp_path} lines {from_line}-{to_line}")
        else:
            self.report_info(f"📄 Reading {disp_path} (all lines)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            selected = lines[(from_line-1 if from_line else 0):(to_line if to_line else None)]
            selected_len = len(selected)
            total_lines = len(lines)
            if from_line and to_line:
                requested = to_line - from_line + 1
                if selected_len < requested:
                    
                    self.report_success(f" ✅ {selected_len} {pluralize('line', selected_len)} (end)")
                elif to_line < total_lines:
                    
                    self.report_success(f" ✅ {selected_len} {pluralize('line', selected_len)} ({total_lines - to_line} lines to end)")
                else:
                    
                    self.report_success(f" ✅ {selected_len} {pluralize('line', selected_len)} (end)")
            else:
                
                self.report_success(f" ✅ {selected_len} {pluralize('line', selected_len)} (full file)")
            # Prepare header
            if from_line and to_line:
                header = f"---\nFile: {disp_path} | Lines: {from_line}-{to_line} (of {total_lines})\n---\n"
            elif from_line:
                header = f"---\nFile: {disp_path} | Lines: {from_line}-END (of {total_lines})\n---\n"
            else:
                header = f"---\nFile: {disp_path} | All lines (total: {total_lines})\n---\n"
            return header + ''.join(selected)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                self.report_error("❗ not found")
                return "❗ not found"
            self.report_error(f" ❌ Error: {e}")
            return f"Error reading file: {e}"


from janito.agent.tools.tools_utils import pluralize
