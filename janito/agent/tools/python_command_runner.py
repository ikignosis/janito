import subprocess
import os
import sys
import tempfile
import threading
from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="python_command_runner")
class PythonCommandRunnerTool(ToolBase):
    """
    Tool to execute Python code using the `python -c` command-line flag.
    Args:
        code (str): The Python code to execute as a string.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
    Returns:
        str: Output and status message, or file paths/line counts if output is large.
    """

    def run(self, code: str, timeout: int = 60) -> str:
        if not code.strip():
            self.report_warning(tr("\u2139\ufe0f Empty code provided."))
            return tr("Warning: Empty code provided. Operation skipped.")
        self.report_info(
            ActionType.EXECUTE, tr("🐍 Running: python -c ...\n{code}\n", code=code)
        )
        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    prefix="python_cmd_stdout_",
                    delete=False,
                    encoding="utf-8",
                ) as stdout_file,
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    prefix="python_cmd_stderr_",
                    delete=False,
                    encoding="utf-8",
                ) as stderr_file,
            ):
                process = subprocess.Popen(
                    [sys.executable, "-c", code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    encoding="utf-8",
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                stdout_lines, stderr_lines = self._stream_process_output(
                    process, stdout_file, stderr_file
                )
                return_code = self._wait_for_process(process, timeout)
                if return_code is None:
                    return tr(
                        "Code timed out after {timeout} seconds.", timeout=timeout
                    )
                stdout_file.flush()
                stderr_file.flush()
                self.report_success(
                    tr("\u2705 Return code {return_code}", return_code=return_code)
                )
                return self._format_result(
                    stdout_file.name, stderr_file.name, return_code
                )
        except Exception as e:
            self.report_error(tr("\u274c Error: {error}", error=e))
            return tr("Error running code: {error}", error=e)

    def _stream_process_output(self, process, stdout_file, stderr_file):
        stdout_lines = 0
        stderr_lines = 0

        def stream_output(stream, file_obj, report_func, count_func):
            nonlocal stdout_lines, stderr_lines
            for line in stream:
                file_obj.write(line)
                file_obj.flush()
                report_func(line)
                if count_func == "stdout":
                    stdout_lines += 1
                else:
                    stderr_lines += 1

        stdout_thread = threading.Thread(
            target=stream_output,
            args=(process.stdout, stdout_file, self.report_stdout, "stdout"),
        )
        stderr_thread = threading.Thread(
            target=stream_output,
            args=(process.stderr, stderr_file, self.report_stderr, "stderr"),
        )
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
        return stdout_lines, stderr_lines

    def _wait_for_process(self, process, timeout):
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            self.report_error(
                tr("\u274c Timed out after {timeout} seconds.", timeout=timeout)
            )
            return None

    def _format_result(self, stdout_file_name, stderr_file_name, return_code):
        with open(stdout_file_name, "r", encoding="utf-8", errors="replace") as out_f:
            stdout_content = out_f.read()
        with open(stderr_file_name, "r", encoding="utf-8", errors="replace") as err_f:
            stderr_content = err_f.read()
        max_lines = 100
        stdout_lines = stdout_content.count("\n")
        stderr_lines = stderr_content.count("\n")

        def head_tail(text, n=10):
            lines = text.splitlines()
            if len(lines) <= 2 * n:
                return "\n".join(lines)
            return "\n".join(
                lines[:n]
                + ["... ({} lines omitted) ...".format(len(lines) - 2 * n)]
                + lines[-n:]
            )

        if stdout_lines <= max_lines and stderr_lines <= max_lines:
            result = f"Return code: {return_code}\n--- STDOUT ---\n{stdout_content}"
            if stderr_content.strip():
                result += f"\n--- STDERR ---\n{stderr_content}"
            return result
        else:
            result = f"stdout_file: {stdout_file_name} (lines: {stdout_lines})\n"
            if stderr_lines > 0 and stderr_content.strip():
                result += f"stderr_file: {stderr_file_name} (lines: {stderr_lines})\n"
            result += f"returncode: {return_code}\n"
            result += "--- STDOUT (head/tail) ---\n" + head_tail(stdout_content) + "\n"
            if stderr_content.strip():
                result += (
                    "--- STDERR (head/tail) ---\n" + head_tail(stderr_content) + "\n"
                )
            result += "Use the get_lines tool to inspect the contents of these files when needed."
            return result
