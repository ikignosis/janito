from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info
import sys
import multiprocessing
import io
from typing import Optional
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
    Returns:
        str: Formatted stdout, stderr, and return code.
    """
    def call(self, code: str) -> str:
        print_info(f"🐍 Executing Python code ...")
        print_info(code)
        self.update_progress("Starting Python code execution...")
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_python_code, args=(code, result_queue))
        process.start()
        process.join()
        if not result_queue.empty():
            result = result_queue.get()
        else:
            result = {'stdout': '', 'stderr': 'No result returned from process.', 'returncode': -1}
        self.update_progress(f"Python code execution completed with return code: {result['returncode']}")
        if result['returncode'] == 0:
            from janito.agent.tools.rich_utils import print_success
            print_success(f"\u2705 Python code executed successfully.")
        else:
            from janito.agent.tools.rich_utils import print_error
            print_error(f"\u274c Python code execution failed with return code {result['returncode']}")
        return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"

ToolHandler.register_tool(PythonExecTool, name="python_exec")
