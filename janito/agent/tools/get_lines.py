import os
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.utils import expand_path, display_path
from janito.agent.tools.tool_base import ToolBase

# Converted get_lines free-function into GetLinesTool
class GetLinesTool(ToolBase):
    def call(self, file_path: str, from_line: int=None, to_line: int=None) -> str:
        original_path = file_path
        file_path = expand_path(file_path)
        disp_path = display_path(original_path, file_path)
        if from_line is None and to_line is None:
            print_info(f"📂 Getting all lines from file: '{disp_path}' ...")
        else:
            print_info(f"📂 Getting lines {from_line} to {to_line} from file: '{disp_path}' ...")
        if not os.path.isfile(file_path):
            print_info(f"ℹ️ File not found: {disp_path}")
            return ""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total_lines = len(lines)
        if from_line is None and to_line is None:
            numbered_content = ''.join(f"{i+1}: {line}" for i, line in enumerate(lines))
            print_success(f"✅ Returned all {total_lines} lines")
            header = f"{original_path}:1 | {total_lines} lines\n"
            return header + numbered_content
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
        header = f"{original_path}:{from_line} | {to_line - from_line + 1} lines\n"
        return header + summary + numbered_content

ToolHandler.register_tool(GetLinesTool, name="get_lines")
