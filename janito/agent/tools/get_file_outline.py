from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
import os
import re
from typing import List


@register_tool(name="get_file_outline")
class GetFileOutlineTool(ToolBase):
    """
    Get an outline of a file's structure.

    Args:
        file_path (str): Path to the file.
    Returns:
        str: Outline of the file's structure, starting with a summary line. Example:
            - "Outline: 5 items (python)\n| Type    | Name        | Start | End | Parent   |\n|---------|-------------|-------|-----|----------|\n| class   | MyClass     | 1     | 20  |          |\n| method  | my_method   | 3     | 10  | MyClass  |\n| function| my_func     | 22    | 30  |          |\n..."
            - "Outline: 100 lines (default)\nFile has 100 lines."
            - "Error reading file: <error message>"
    """

    def call(self, file_path: str) -> str:
        from janito.agent.tools.tools_utils import display_path

        disp_path = display_path(file_path)
        self.report_info(f"📄 Getting outline for: {disp_path}")

        try:
            ext = os.path.splitext(file_path)[1].lower()
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if ext == ".py":
                outline_items = self._parse_python_outline(lines)
                outline_type = "python"
                table = self._format_outline_table(outline_items)
                self.report_success(f"✅ {len(outline_items)} items ({outline_type})")
                return f"Outline: {len(outline_items)} items ({outline_type})\n" + table
            else:
                outline_type = "default"
                self.report_success(f"✅ {len(lines)} lines ({outline_type})")
                return f"Outline: {len(lines)} lines ({outline_type})\nFile has {len(lines)} lines."
        except Exception as e:
            self.report_error(f"❌ Error reading file: {e}")
            return f"Error reading file: {e}"

    def _parse_python_outline(self, lines: List[str]):
        # Regex for class, function, and method definitions
        class_pat = re.compile(r"^(\s*)class\s+(\w+)")
        func_pat = re.compile(r"^(\s*)def\s+(\w+)")
        outline = []
        stack = []  # (name, type, indent, start, parent)
        for idx, line in enumerate(lines):
            class_match = class_pat.match(line)
            func_match = func_pat.match(line)
            indent = len(line) - len(line.lstrip())
            if class_match:
                name = class_match.group(2)
                parent = stack[-1][1] if stack and stack[-1][0] == "class" else ""
                stack.append(("class", name, indent, idx + 1, parent))
            elif func_match:
                name = func_match.group(2)
                parent = (
                    stack[-1][1]
                    if stack
                    and stack[-1][0] in ("class", "function")
                    and indent > stack[-1][2]
                    else ""
                )
                stack.append(("function", name, indent, idx + 1, parent))
            # Pop stack if indentation decreases
            while stack and indent < stack[-1][2]:
                popped = stack.pop()
                outline.append(
                    {
                        "type": (
                            popped[0]
                            if popped[0] != "function" or popped[3] == 1
                            else ("method" if popped[4] else "function")
                        ),
                        "name": popped[1],
                        "start": popped[3],
                        "end": idx,
                        "parent": popped[4],
                    }
                )
        # Close any remaining stack
        last_idx = len(lines)
        while stack:
            popped = stack.pop()
            outline.append(
                {
                    "type": (
                        popped[0]
                        if popped[0] != "function" or popped[3] == 1
                        else ("method" if popped[4] else "function")
                    ),
                    "name": popped[1],
                    "start": popped[3],
                    "end": last_idx,
                    "parent": popped[4],
                }
            )
        # Sort by start line
        outline.sort(key=lambda x: x["start"])
        return outline

    def _format_outline_table(self, outline_items: List[dict]) -> str:
        if not outline_items:
            return "No classes or functions found."
        header = "| Type    | Name        | Start | End | Parent   |\n|---------|-------------|-------|-----|----------|"
        rows = []
        for item in outline_items:
            rows.append(
                f"| {item['type']:<7} | {item['name']:<11} | {item['start']:<5} | {item['end']:<3} | {item['parent']:<8} |"
            )
        return header + "\n" + "\n".join(rows)
