from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import subprocess
import tempfile
import sys
import os
import threading
from janito.agent.runtime_config import runtime_config


@register_tool(name="run_bash_command")
class RunBashCommandTool(ToolBase):
    """
    Execute a non-interactive command using the bash shell and capture live output.
    This tool explicitly invokes the 'bash' shell (not just the system default shell), so it requires bash to be installed and available in the system PATH. On Windows, this will only work if bash is available (e.g., via WSL, Git Bash, or similar).
    Args:
        command (str): The bash command to execute.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
        requires_user_input (bool, optional): If True, warns that the command may require user input and might hang. Defaults to False. Non-interactive commands are preferred for automation and reliability.
    Returns:
        str: File paths and line counts for stdout and stderr.
    """

    def _stream_output(
        self,
        stream,
        report_func,
        accum=None,
        file_obj=None,
        count_func=None,
        counter=None,
    ):
        for line in stream:
            if accum is not None:
                accum.append(line)
            if file_obj is not None:
                file_obj.write(line)
                file_obj.flush()
            report_func(line)
            if counter is not None and count_func is not None:
                counter[count_func] += 1

    def _handle_all_out(self, process, timeout):
        stdout_accum = []
        stderr_accum = []
        stdout_thread = threading.Thread(
            target=self._stream_output,
            args=(process.stdout, self.report_stdout, stdout_accum),
        )
        stderr_thread = threading.Thread(
            target=self._stream_output,
            args=(process.stderr, self.report_stderr, stderr_accum),
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            self.report_error(
                tr(" ❌ Timed out after {timeout} seconds.", timeout=timeout)
            )
            return tr("Command timed out after {timeout} seconds.", timeout=timeout)
        stdout_thread.join()
        stderr_thread.join()
        self.report_success(
            tr(" ✅ return code {return_code}", return_code=return_code)
        )
        stdout_content = "".join(stdout_accum)
        stderr_content = "".join(stderr_accum)
        result = tr(
            "Return code: {return_code}\n--- STDOUT ---\n{stdout_content}",
            return_code=return_code,
            stdout_content=stdout_content,
        )
        if stderr_content.strip():
            result += tr(
                "\n--- STDERR ---\n{stderr_content}", stderr_content=stderr_content
            )
        return result

    def _handle_file_out(self, process, timeout):
        max_lines = 100
        with (
            tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="run_bash_stdout_",
                delete=False,
                encoding="utf-8",
            ) as stdout_file,
            tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="run_bash_stderr_",
                delete=False,
                encoding="utf-8",
            ) as stderr_file,
        ):
            counter = {"stdout": 0, "stderr": 0}
            stdout_thread = threading.Thread(
                target=self._stream_output,
                args=(
                    process.stdout,
                    self.report_stdout,
                    None,
                    stdout_file,
                    "stdout",
                    counter,
                ),
            )
            stderr_thread = threading.Thread(
                target=self._stream_output,
                args=(
                    process.stderr,
                    self.report_stderr,
                    None,
                    stderr_file,
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
                    tr(" ❌ Timed out after {timeout} seconds.", timeout=timeout)
                )
                return tr("Command timed out after {timeout} seconds.", timeout=timeout)
            stdout_thread.join()
            stderr_thread.join()
            stdout_file.flush()
            stderr_file.flush()
            self.report_success(
                tr(" ✅ return code {return_code}", return_code=return_code)
            )
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_content = stdout_file.read()
            stderr_content = stderr_file.read()
            stdout_lines = stdout_content.count("\n")
            stderr_lines = stderr_content.count("\n")
            if stdout_lines <= max_lines and stderr_lines <= max_lines:
                result = tr(
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
                result = tr(
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
                    return_code=return_code,
                )
                return result

    def run(
        self,
        command: str,
        timeout: int = 60,
        require_confirmation: bool = False,
        requires_user_input: bool = False,
    ) -> str:
        if not command.strip():
            self.report_warning(tr("ℹ️ Empty command provided."))
            return tr("Warning: Empty command provided. Operation skipped.")
        self.report_info(
            ActionType.EXECUTE,
            tr("🖥️ Run bash command: {command} ...\n", command=command),
        )
        if requires_user_input:
            self.report_warning(
                tr(
                    "⚠️  Warning: This command might be interactive, require user input, and might hang."
                )
            )
            sys.stdout.flush()
        try:
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
            if runtime_config.get("all_out"):
                return self._handle_all_out(process, timeout)
            else:
                return self._handle_file_out(process, timeout)
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error running command: {error}", error=e)
