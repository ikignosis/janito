from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import subprocess
import tempfile
import sys
import os


@register_tool(name="run_bash_command")
class RunBashCommandTool(ToolBase):
    """
    Execute a non-interactive command using the bash shell and capture live output.
    This tool explicitly invokes the 'bash' shell (not just the system default shell), so it requires bash to be installed and available in the system PATH. On Windows, this will only work if bash is available (e.g., via WSL, Git Bash, or similar).
    Args:
        command (str): The bash command to execute.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
        interactive (bool, optional): If True, warns that the command may require user interaction. Defaults to False. Non-interactive commands are preferred for automation and reliability.
    Returns:
        str: File paths and line counts for stdout and stderr.
    """

    def run(
        self,
        command: str,
        timeout: int = 60,
        require_confirmation: bool = False,
        interactive: bool = False,
    ) -> str:
        if not command.strip():
            self.report_warning(tr("ℹ️ Empty command provided."))
            return tr("Warning: Empty command provided. Operation skipped.")
        self.report_info(tr("🖥️ Running bash command: {command} ...\n", command=command))
        if interactive:
            self.report_warning(
                tr(
                    "⚠️  Warning: This command might be interactive, require user input, and might hang."
                )
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
                stdout_lines = 0
                stderr_lines = 0
                stdout_content = []
                stderr_content = []
                max_lines = 100
                import threading

                def stream_reader(
                    stream, file_handle, report_func, content_list, line_counter
                ):
                    for line in iter(stream.readline, ""):
                        file_handle.write(line)
                        file_handle.flush()
                        report_func(line)
                        content_list.append(line)
                        line_counter[0] += 1
                    stream.close()

                stdout_counter = [0]
                stderr_counter = [0]
                stdout_thread = threading.Thread(
                    target=stream_reader,
                    args=(
                        process.stdout,
                        stdout_file,
                        self.report_stdout,
                        stdout_content,
                        stdout_counter,
                    ),
                )
                stderr_thread = threading.Thread(
                    target=stream_reader,
                    args=(
                        process.stderr,
                        stderr_file,
                        self.report_stderr,
                        stderr_content,
                        stderr_counter,
                    ),
                )
                stdout_thread.start()
                stderr_thread.start()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.report_error(
                        tr(" ❌ Timed out after {timeout} seconds.", timeout=timeout)
                    )
                    return tr(
                        "Command timed out after {timeout} seconds.", timeout=timeout
                    )
                stdout_thread.join()
                stderr_thread.join()
                stdout_lines = stdout_counter[0]
                stderr_lines = stderr_counter[0]
                self.report_success(
                    tr(" ✅ return code {return_code}", return_code=process.returncode)
                )
                warning_msg = ""
                if interactive:
                    warning_msg = tr(
                        "⚠️  Warning: This command might be interactive, require user input, and might hang.\n"
                    )
                if stdout_lines <= max_lines and stderr_lines <= max_lines:
                    with open(
                        stdout_file.name, "r", encoding="utf-8", errors="replace"
                    ) as out_f:
                        stdout_content_str = out_f.read()
                    with open(
                        stderr_file.name, "r", encoding="utf-8", errors="replace"
                    ) as err_f:
                        stderr_content_str = err_f.read()
                    result = warning_msg + tr(
                        "Return code: {return_code}\n--- STDOUT ---\n{stdout_content}",
                        return_code=process.returncode,
                        stdout_content=stdout_content_str,
                    )
                    if stderr_content_str.strip():
                        result += tr(
                            "\n--- STDERR ---\n{stderr_content}",
                            stderr_content=stderr_content_str,
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
                        "returncode: {return_code}\nUse the get_lines tool to inspect the contents of these files when needed.",
                        return_code=process.returncode,
                    )
                    return result
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error running command: {error}", error=e)
