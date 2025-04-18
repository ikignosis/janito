

import sys
import multiprocessing
import io
from typing import Optional
from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool


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
@register_tool(name="python_exec")
class PythonExecTool(ToolBase):
    """
    Execute Python code in a separate process and capture output.
    Useful for exact calculations, retrieving the current date and time, or performing any Python-supported operation.
    Args:
        code (str): The Python code to execute.
    Returns:
        str: Formatted stdout, stderr, and return code.
    """
    def call(self, code: str) -> str:
        """
        Execute arbitrary Python code, including exact calculations, getting the current date, time, and more.

        Args:
            code (str): The Python code to execute.

        Returns:
            str: Formatted stdout, stderr, and return code.
        """
        self.report_info(f"🐍 Executing Python code ...")
        self.report_info(code)

        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_python_code, args=(code, result_queue))
        process.start()
        process.join()
        if not result_queue.empty():
            result = result_queue.get()
        else:
            result = {'stdout': '', 'stderr': 'No result returned from process.', 'returncode': -1}

        if result['returncode'] == 0:

            self.report_success(f"✅ Python code executed")
        else:

            self.report_error(f"\u274c Python code execution failed with return code {result['returncode']}")
        return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"


