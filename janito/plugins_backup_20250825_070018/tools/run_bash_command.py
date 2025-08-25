from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.plugins.tools.decorators import register_core_tool
from janito.i18n import tr
import subprocess
import tempfile
import sys
import os
import threading


@register_core_tool
class RunBashCommand(ToolBase):
    """
    Execute a non-interactive command using the bash shell and capture live output.
    This tool explicitly invokes the 'bash' shell (not just the system default shell), so it requires bash to be installed and available in the system PATH. On Windows, this will only work if bash is available (e.g., via WSL, Git Bash, or similar).

    Args:
        command (str): The bash command to execute.
        timeout (int): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool): If True, require user confirmation before running. Defaults to False.
        requires_user_input (bool): If True, warns that the command may require user input and might hang. Defaults to False. Non-interactive commands are preferred for automation and reliability.
        silent (bool): If True, suppresses progress and status messages. Defaults to False.

    Returns:
        str: File paths and line counts for stdout and stderr.
    """

    permissions = ToolPermissions(execute=True)
    tool_name = "run_bash_command"

    def _stream_output(self, stream, file_obj, report_func, count_func, counter):
        for line in stream:
            file_obj.write(line)
            file_obj.flush()
            report_func(line.rstrip("\r\n"), ReportAction.EXECUTE)
            if count_func == "stdout":
                counter["stdout"] += 1
            else:
                counter["stderr"] += 1

    def run(
        self,
        command: str,
        timeout: int = 60,
        require_confirmation: bool = False,
        requires_user_input: bool = False,
        silent: bool = False,
    ) -> str:
        if not command.strip():
            self.report_warning(tr("ℹ️ Empty command provided."), ReportAction.EXECUTE)
            return tr("Warning: Empty command provided. Operation skipped.")
        if not silent:
            self.report_action(
                tr("🖥️  Run bash command: {command} ...\n", command=command),
                ReportAction.EXECUTE,
            )
        else:
            self.report_action(tr("⚡ Executing..."), ReportAction.EXECUTE)
        if requires_user_input and not silent:
            self.report_warning(
                tr(
                    "⚠️  Warning: This command might be interactive, require user input, and might hang."
                ),
                ReportAction.EXECUTE,
            )
            sys.stdout.flush()
        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w+", prefix="run_bash_stdout_", delete=False, encoding="utf-8"
                ) as stdout_file,
                tempfile.NamedTemporaryFile(
                    mode="w+", prefix="run_bash_stderr_", delete=False, encoding="utf-8"
                ) as stderr_file,
            ):
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["LC_ALL"] = "C.UTF-8"
                env["LANG"] = "C.UTF-8"
                process = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    env=env,
                )
                counter = {"stdout": 0, "stderr": 0}
                stdout_thread = threading.Thread(
                    target=self._stream_output,
                    args=(
                        process.stdout,
                        stdout_file,
                        self.report_stdout,
                        "stdout",
                        counter,
                    ),
                )
                stderr_thread = threading.Thread(
                    target=self._stream_output,
                    args=(
                        process.stderr,
                        stderr_file,
                        self.report_stderr,
                        "stderr",
                        counter,
                    ),
                )
                stdout_thread.start()
                stderr_thread.start()
                try:
                    return_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.report_error(
                        tr(
                            " ❌ Timed out after {timeout} seconds.",
                            timeout=timeout,
                        ),
                        ReportAction.EXECUTE,
                    )
                    return tr(
                        "Command timed out after {timeout} seconds.", timeout=timeout
                    )
                stdout_thread.join()
                stderr_thread.join()
                stdout_file.flush()
                stderr_file.flush()
                if not silent:
                    self.report_success(
                        tr(
                            " ✅ return code {return_code}",
                            return_code=return_code,
                        ),
                        ReportAction.EXECUTE,
                    )
                max_lines = 100
                # Read back the output for summary
                stdout_file.seek(0)
                stderr_file.seek(0)
                stdout_content = stdout_file.read()
                stderr_content = stderr_file.read()
                stdout_lines = counter["stdout"]
                stderr_lines = counter["stderr"]
                warning_msg = ""
                if requires_user_input:
                    warning_msg = tr(
                        "⚠️  Warning: This command might be interactive, require user input, and might hang.\n"
                    )
                if stdout_lines <= max_lines and stderr_lines <= max_lines:
                    result = warning_msg + tr(
                        "Return code: {return_code}\n--- STDOUT ---\n{stdout_content}",
                        return_code=return_code,
                        stdout_content=stdout_content,
                    )
                    if stderr_content.strip():
                        result += tr(
                            "\n--- STDERR ---\n{stderr_content}",
                            stderr_content=stderr_content,
                        )
                    return result
                else:
                    result = warning_msg + tr(
                        "[LARGE OUTPUT]\nstdout_file: {stdout_file} (lines: {stdout_lines})\n",
                        stdout_file=stdout_file.name,
                        stdout_lines=stdout_lines,
                    )
                    if stderr_lines > 0:
                        result += tr(
                            "stderr_file: {stderr_file} (lines: {stderr_lines})\n",
                            stderr_file=stderr_file.name,
                            stderr_lines=stderr_lines,
                        )
                    result += tr(
                        "returncode: {return_code}\nUse the view_file tool to inspect the contents of these files when needed.",
                        return_code=return_code,
                    )
                    return result
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e), ReportAction.EXECUTE)
            return tr("Error running command: {error}", error=e)
