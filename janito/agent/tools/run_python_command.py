import multiprocessing
import io
import sys
import time
from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

def _run_python_code(code: str, result_queue):
    import contextlib
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exec(code, {'__name__': '__main__'})
            returncode = 0
        except Exception as e:
            stderr.write(str(e))
            returncode = 1
    result_queue.put({
        'stdout': stdout.getvalue(),
        'stderr': stderr.getvalue(),
        'returncode': returncode
    })

@register_tool(name="run_python_command")
class RunPythonCommandTool(ToolBase):
    """
    Execute Python code in a separate process and capture output.
    Args:
        code (str): The Python code to execute.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
        interactive (bool, optional): If True, warns that the command may require user interaction. Defaults to False.
    Returns:
        str: Formatted stdout, stderr, and return code.
    """
    def call(self, code: str, timeout: int = 60, require_confirmation: bool = False, interactive: bool = False) -> str:
        if not code.strip():
            self.report_warning("⚠️ Warning: Empty code provided. Operation skipped.")
            return "Warning: Empty code provided. Operation skipped."
        self.report_info(f"🐍 Running Python code:\n{code}\n")
        if interactive:
            self.report_info("⚠️  Warning: This code might be interactive, require user input, and might hang.")
        sys.stdout.flush()
        if require_confirmation:
            confirmed = self.confirm_action("Do you want to execute this Python code?")
            if not confirmed:
                self.report_warning("Execution cancelled by user.")
                return "Execution cancelled by user."
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_python_code, args=(code, result_queue))
        process.start()
        process.join(timeout=timeout)
        if process.is_alive():
            process.terminate()
            self.report_error(f" ❌ Timed out after {timeout} seconds.")
            return f"Code timed out after {timeout} seconds."
        if not result_queue.empty():
            result = result_queue.get()
        else:
            result = {'stdout': '', 'stderr': 'No result returned from process.', 'returncode': -1}
        if result['returncode'] == 0:
            self.report_success("✅ Python code executed")
        else:
            self.report_error(f"❌ Python code execution failed with return code {result['returncode']}")
        return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"
