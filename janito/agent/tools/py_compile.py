from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


from typing import Optional
import py_compile

@register_tool(name="py_compile")
class PyCompileTool(ToolBase):
    """Validate a Python file by compiling it with py_compile."""
    def call(self, file_path: str, doraise: Optional[bool] = True) -> str:
        self.report_info(f"[py_compile] Compiling Python file: {file_path}")

        try:
            py_compile.compile(file_path, doraise=doraise)
            self.report_success(f"[py_compile] Compiled: {file_path}")
            return f"Compiled successfully: {file_path}"
        except py_compile.PyCompileError as e:
            self.report_error(f"[py_compile] Compile error: {e}")
            return f"Compile error: {e}"
        except Exception as e:
            self.report_error(f"[py_compile] Error: {e}")
            return f"Error: {e}"
