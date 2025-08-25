import subprocess
import os
import sys
import tempfile
import threading
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.plugins.tools.decorators import register_core_tool
from janito.i18n import tr


@register_core_tool
class PythonFileRun(ToolBase):
    """
    Tool to execute a specified Python script file.

    Args:
        path (str): Path to the Python script file to execute.
        timeout (int): Timeout in seconds for the command. Defaults to 60.
        silent (bool): If True, suppresses progress and status messages. Defaults to False.

    Returns:
        str: Output and status message, or file paths/line counts if output is large.
    """

    permissions = ToolPermissions(execute=True)
    tool_name = "python_file_run"

    def run(self, path: str, timeout: int = 60, silent: bool = False) -> str:
        from janito.tools.path_utils import expand_path

        path = expand_path(path)
        if not silent:
            self.report_action(
                tr("🚀 Running: python {path}", path=path),
                ReportAction.EXECUTE,
            )
            self.report_stdout("\n")
        else:
            self.report_action(tr("⚡ Executing..."), ReportAction.EXECUTE)
        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    prefix="python_file_stdout_",
                    delete=False,
                    encoding="utf-8",
                ) as stdout_file,
                tempfile.NamedTemporaryFile(
                    mode="w+",
                    prefix="python_file_stderr_",
                    delete=False,
                    encoding="utf-8",
                ) as stderr_file,
            ):
                process = subprocess.Popen(
                    [sys.executable, path],
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
                if not silent:
                    self.report_success(
                        tr("✅ Return code {return_code}", return_code=return_code),
                        ReportAction.EXECUTE,
                    )
                return self._format_result(
                    stdout_file.name, stderr_file.name, return_code
                )
        except Exception as e:
            self.report_error(tr("❌ Error: {error}", error=e), ReportAction.EXECUTE)
            return tr("Error running file: {error}", error=e)

    def _stream_process_output(self, process, stdout_file, stderr_file):
        stdout_lines = 0
        stderr_lines = 0

        def stream_output(stream, file_obj, report_func, count_func):
            nonlocal stdout_lines, stderr_lines
            for line in stream:
                file_obj.write(line)
                file_obj.flush()
                # Always supply a default action for stdout/stderr reporting
                from janito.report_events import ReportAction

                report_func(line.rstrip("\r\n"), ReportAction.EXECUTE)
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
                tr("❌ Timed out after {timeout} seconds.", timeout=timeout),
                ReportAction.EXECUTE,
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
            result = f"Return code: {return_code}\n--- python_file_run: STDOUT ---\n{stdout_content}"
            if stderr_content.strip():
                result += f"\n--- python_file_run: STDERR ---\n{stderr_content}"
            return result
        else:
            result = f"stdout_file: {stdout_file_name} (lines: {stdout_lines})\n"
            if stderr_lines > 0 and stderr_content.strip():
                result += f"stderr_file: {stderr_file_name} (lines: {stderr_lines})\n"
            result += f"returncode: {return_code}\n"
            result += (
                "--- python_file_run: STDOUT (head/tail) ---\n"
                + head_tail(stdout_content)
                + "\n"
            )
            if stderr_content.strip():
                result += (
                    "--- python_file_run: STDERR (head/tail) ---\n"
                    + head_tail(stderr_content)
                    + "\n"
                )
            result += "Use the view_file tool to inspect the contents of these files when needed."
            return result
