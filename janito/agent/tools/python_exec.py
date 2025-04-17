from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info
import sys
import multiprocessing
import io
from typing import Callable, Optional
from janito.agent.tools.tool_base import ToolBase


def _run_python_code(code: str, result_queue):
    import traceback
    import contextlib
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exec(code, {'__name__': '__main__'})
    result_queue.put({
        'stdout': stdout.getvalue(),
        'stderr': stderr.getvalue(),
        'returncode': 0
    })


# Converted python_exec function into PythonExecTool subclass
class PythonExecTool(ToolBase):
    """
    Execute Python code in a separate process and capture output.

    Args:
        code (str): The Python code to execute.
        on_progress (Optional[Callable[[dict], None]]): Optional callback for streaming progress (not used).

    Returns:
        str: Formatted stdout, stderr, and return code.
    """
    def call(self, code: str, on_progress: Optional[Callable[[dict], None]] = None) -> str:
        print_info(f"🐍 Executing Python code ...")
        print_info(code)
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_python_code, args=(code, result_queue))
        process.start()
        process.join()
        if not result_queue.empty():
            result = result_queue.get()
        else:
            result = {'stdout': '', 'stderr': 'No result returned from process.', 'returncode': -1}
        print_info(f"🐍 Python code execution completed.")
        print_info(f"🐍 Python code return code: {result['returncode']}")
        return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"

ToolHandler.register_tool(PythonExecTool, name="python_exec")
