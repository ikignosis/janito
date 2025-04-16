import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number

@ToolHandler.register_tool
def get_lines(
    file_path: str,
    from_line: int = None,
    to_line: int = None
) -> str:
    """
    Get lines from a file, optionally with a summary of lines outside the viewed range.
    Always returns the total number of lines in the file at the top of the output.
    
    Parameters:
      - file_path (string): Path to the file.
      - from_line (integer, optional): First line to view (1-indexed). If omitted with to_line, returns all lines.
      - to_line (integer, optional): Last line to view (inclusive, 1-indexed, and cannot be more than 200 lines from from_line).
    
    If both from_line and to_line are omitted, returns all lines in the file.
    It is recommended to request at least 100 lines or the full file for more efficient context building.
    """
    if from_line is None and to_line is None:
        print_info(f"📂 get_lines | Path: {format_path(file_path)} | All lines requested")
    else:
        print_info(f"📂 get_lines | Path: {format_path(file_path)} | Lines ({from_line}-{to_line})")
    if not os.path.isfile(file_path):
        print_info(f"ℹ️ File not found: {file_path}")
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    total_lines = len(lines)
    if from_line is None and to_line is None:
        numbered_content = ''.join(f"{i+1}: {line}" for i, line in enumerate(lines))
        print_success(f"✅ Returned all {total_lines} lines")
        return f"Total lines in file: {total_lines}\n" + numbered_content
    # Validate range
    if from_line is None or to_line is None:
        print_error(f"❌ Both from_line and to_line must be provided, or neither.")
        return ""
    if from_line < 1 or to_line < from_line or (to_line - from_line > 200):
        print_error(f"❌ Invalid line range: {from_line}-{to_line} for file with {total_lines} lines.")
        return ""
    if to_line > total_lines:
        to_line = total_lines
    selected = lines[from_line-1:to_line]
    numbered_content = ''.join(f"{i}: {line}" for i, line in zip(range(from_line, to_line+1), selected))
    before = lines[:from_line-1]
    after = lines[to_line:]
    before_summary = f"... {len(before)} lines before ...\n" if before else ""
    after_summary = f"... {len(after)} lines after ...\n" if after else ""
    summary = before_summary + after_summary
    if from_line == 1 and to_line == total_lines:
        print_success(f"✅ Returned all {total_lines} lines")
    else:
        print_success(f"✅ Returned lines {from_line} to {to_line} of {total_lines}")
    total_line_info = f"Total lines in file: {total_lines}\n"
    return total_line_info + summary + numbered_content
