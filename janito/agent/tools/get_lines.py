from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error

class GetLinesTool(ToolBase):
    """Get specific lines from a file."""
    def call(self, file_path: str, from_line: int=None, to_line: int=None) -> str:
        import os
        def _display_path(path):
            import os
            if os.path.isabs(path):
                return path
            return os.path.relpath(path)
        disp_path = _display_path(file_path)
        if from_line and to_line:
            count = to_line - from_line + 1
            print_info(f"📄 Reading {disp_path}:{from_line} ({count} lines)", end="")
        else:
            print_info(f"📄 Reading {disp_path} (all lines)", end="")
        self.update_progress(f"Getting lines {from_line} to {to_line} from {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            selected = lines[(from_line-1 if from_line else 0):(to_line if to_line else None)]
            if from_line and to_line:
                print_success(f" ✅ {to_line - from_line + 1} lines read")
            else:
                print_success(f" ✅ {len(lines)} lines read")
            return ''.join(selected)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                print_error(f"❗ not found")
                return "❗ not found"
            print_error(f" ❌ Error: {e}")
            return f"Error reading file: {e}"

ToolHandler.register_tool(GetLinesTool, name="get_lines")
