from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

from typing import Optional
import py_compile


@register_tool(name="py_compile_file")
class PyCompileFileTool(ToolBase):
    """
    Validate a Python file by compiling it with py_compile.
    Useful to validate python files after changing them, especially after import changes.

    Args:
        file_path (str): Path to the Python file to compile.
        doraise (bool, optional): Whether to raise exceptions on compilation errors. Defaults to True.
    Returns:
        str: Compilation status message. Example:
            - "✅ Compiled"
            - "Compile error: <error message>"
            - "Error: <error message>"
    """

    def call(self, file_path: str, doraise: Optional[bool] = True) -> str:
        self.report_info(f"🛠️  Compiling Python file: {file_path}")

        if not (file_path.endswith(".py") or file_path.endswith(".pyw")):
            msg = f"Error: {file_path} is not a Python (.py/.pyw) file."
            self.report_error(f" [py_compile_file] {msg}")
            return msg
        try:
            py_compile.compile(file_path, doraise=doraise)
            self.report_success(" ✅ Compiled")
            return "✅ Compiled"
        except py_compile.PyCompileError as e:
            self.report_error(f" [py_compile_file] Compile error: {e}")
            return f"Compile error: {e}"
        except Exception as e:
            self.report_error(f" [py_compile_file] Error: {e}")
            return f"Error: {e}"
