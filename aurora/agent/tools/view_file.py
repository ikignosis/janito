import os
from aurora.agent.tool_handler import ToolHandler
from aurora.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number

@ToolHandler.register_tool
def view_file(path: str, start_line: int = 1, end_line: int = None) -> str:
    """
    View the contents of a file or list the contents of a directory.

    path: The path of the file or directory to view
    start_line: The starting line number (1-based, default: 1)
    end_line: The ending line number (inclusive). If None, view until end of file.
    """
    print_info(f"📂 View '{format_path(path)}' lines {format_number(start_line)} to {format_number(end_line) if end_line else 'EOF'}")
    if os.path.isdir(path):
        files = os.listdir(path)
        print_success(f"✅ {format_number(len(files))} items")
        return "\n".join(files)
    else:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if end_line is None or end_line > total_lines:
            end_line = total_lines

        # Adjust for 0-based index
        start_idx = max(start_line - 1, 0)
        end_idx = end_line

        selected_lines = lines[start_idx:end_idx]
        content = ''.join(selected_lines)
        print_success(f"✅ Returned lines {format_number(start_line)} to {format_number(end_line)} of {format_number(total_lines)}")
        return content
