from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from typing import Optional
import py_compile

class PyCompileTool(ToolBase):
    """Validate a Python file by compiling it with py_compile."""
    def call(self, file_path: str, doraise: Optional[bool] = True) -> str:
        print_info(f"[py_compile] Compiling Python file: {file_path}", end="")
        self.update_progress(f"Compiling Python file: {file_path}")
        try:
            py_compile.compile(file_path, doraise=doraise)
            print_success(f"[py_compile] Compiled successfully: {file_path}")
            return f"Compiled successfully: {file_path}"
        except py_compile.PyCompileError as e:
            print_error(f"[py_compile] Compile error: {e}")
            return f"Compile error: {e}"
        except Exception as e:
            print_error(f"[py_compile] Error: {e}")
            return f"Error: {e}"

ToolHandler.register_tool(PyCompileTool, name="py_compile_file")
