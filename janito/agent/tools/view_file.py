import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path, format_number

@ToolHandler.register_tool
def view_file(
    AbsolutePath: str,
    StartLine: int,
    EndLine: int,
    IncludeSummaryOfOtherLines: bool
) -> str:
    """
    View contents of a file, optionally with a summary of lines outside the viewed range.
    Parameters:
      - AbsolutePath (string): Path to the file.
      - StartLine (integer): First line to view (1-indexed).
      - EndLine (integer): Last line to view (inclusive, 1-indexed, and cannot be more than 200 lines from StartLine).
      - IncludeSummaryOfOtherLines (boolean): If true, also return a summary of other lines.
    """
    print_info(f"📂 view_file | Path: {format_path(AbsolutePath)} | StartLine: {StartLine} | EndLine: {EndLine} | IncludeSummary: {IncludeSummaryOfOtherLines}")
    if not os.path.isfile(AbsolutePath):
        print_error(f"❌ Not a file: {AbsolutePath}")
        return ""
    with open(AbsolutePath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    total_lines = len(lines)
    # Validate line range (1-indexed)
    # If EndLine is greater than the file, adjust to last line
    if StartLine < 1 or EndLine < StartLine or (EndLine - StartLine > 200):
        print_error(f"❌ Invalid line range: {StartLine}-{EndLine} for file with {total_lines} lines.")
        return ""
    if EndLine > total_lines:
        EndLine = total_lines
    # Convert to 0-indexed for slicing
    selected = lines[StartLine-1:EndLine]
    # Prefix each line with its 1-based line number
    numbered_content = ''.join(f"{i}: {line}" for i, line in zip(range(StartLine, EndLine+1), selected))
    summary = ""
    if IncludeSummaryOfOtherLines:
        before = lines[:StartLine-1]
        after = lines[EndLine:]
        before_summary = f"... {len(before)} lines before ...\n" if before else ""
        after_summary = f"... {len(after)} lines after ...\n" if after else ""
        summary = before_summary + after_summary
    print_success(f"✅ Returned lines {StartLine} to {EndLine} of {total_lines}")
    return summary + numbered_content
