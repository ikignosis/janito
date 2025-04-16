from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info
import sys
import multiprocessing
import io
from typing import Callable, Optional


def _run_python_code(code: str, result_queue):
    import traceback
    import contextlib
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(code, {'__name__': '__main__'})
        result_queue.put({
            'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue(),
            'returncode': 0
        })
    except Exception:
        result_queue.put({
            'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue() + traceback.format_exc(),
            'returncode': 1
        })

@ToolHandler.register_tool
def python_exec(code: str, on_progress: Optional[Callable[[dict], None]] = None) -> str:
    """
    code: The Python code to execute.
    on_progress: Optional callback function for streaming progress updates (not used).

    Execute Python code in a separate process and capture output.

    Returns:
    str: A formatted message string containing stdout, stderr, and return code.
    """
    print_info(f"[python_exec] Executing Python code:")
    print_info(code)
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_run_python_code, args=(code, result_queue))
    process.start()
    process.join()
    if not result_queue.empty():
        result = result_queue.get()
    else:
        result = {'stdout': '', 'stderr': 'No result returned from process.', 'returncode': -1}
    print_info(f"[python_exec] Execution completed.")
    print_info(f"[python_exec] Return code: {result['returncode']}")
    return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"
