from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info
from janito.agent.tools.utils import expand_path
import py_compile
from typing import Optional

@ToolHandler.register_tool
def py_compile_file(path: str, doraise: Optional[bool] = True) -> str:
    """
    Validate a Python file by compiling it with py_compile.
    This tool should be used to validate Python files after changes.

    Args:
        path (str): Path to the Python file to validate.
        doraise (Optional[bool]): If True, raise exceptions on compilation errors. Default is True.

    Returns:
        str: Success message or error details if compilation fails.
    """
    path = expand_path(path)
    print_info(f"[py_compile_file] Validating Python file: {path}")
    try:
        py_compile.compile(path, doraise=doraise)
        return f"Validation successful: {path} is a valid Python file."
    except FileNotFoundError:
        return f"Validation failed: File not found: {path}"
    except py_compile.PyCompileError as e:
        return f"Validation failed: {e}"
