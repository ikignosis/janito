from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import subprocess
import os
import tempfile
import threading
from janito.agent.runtime_config import runtime_config


@register_tool(name="run_powershell_command")
class RunPowerShellCommandTool(ToolBase):
    """
    Execute a non-interactive command using the PowerShell shell and capture live output.
    This tool explicitly invokes 'powershell.exe' (on Windows) or 'pwsh' (on other platforms if available).
    All commands are automatically prepended with UTF-8 output encoding:
    $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
    For file output, it is recommended to use -Encoding utf8 in your PowerShell commands (e.g., Out-File -Encoding utf8) to ensure correct file encoding.
    Args:
        command (str): The PowerShell command to execute. This string is passed directly to PowerShell using the --Command argument (not as a script file).
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
        requires_user_input (bool, optional): If True, warns that the command may require user input and might hang. Defaults to False. Non-interactive commands are preferred for automation and reliability.
    Returns:
        str: Output and status message, or file paths/line counts if output is large.
    """

    def _confirm_and_warn(self, command, require_confirmation, requires_user_input):
        if requires_user_input:
            self.report_warning(
                tr(
                    "⚠️  Warning: This command might be interactive, require user input, and might hang."
                )
            )
        if require_confirmation:
            confirmed = self.ask_user_confirmation(
                tr(
                    "About to run PowerShell command: {command}\nContinue?",
                    command=command,
                )
            )
            if not confirmed:
                self.report_warning(tr("⚠️ Execution cancelled by user."))
                return False
        return True

    def _launch_process(self, shell_exe, command_with_encoding):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.Popen(
            [
                shell_exe,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command_with_encoding,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            env=env,
        )

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
        stdout = "".join(stdout_accum)
        stderr = "".join(stderr_accum)
        result = f"Return code: {return_code}\n--- STDOUT ---\n{stdout}"
        if stderr and stderr.strip():
            result += f"\n--- STDERR ---\n{stderr}"
        return result

    def _handle_file_out(self, process, timeout):
        with (
            tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="run_powershell_stdout_",
                delete=False,
                encoding="utf-8",
            ) as stdout_file,
            tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="run_powershell_stderr_",
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
            return self._format_result(stdout_file.name, stderr_file.name, return_code)

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
        encoding_prefix = "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        command_with_encoding = encoding_prefix + command
        self.report_info(
            ActionType.EXECUTE,
            tr(
                "🖥️ Running PowerShell command: {command} ...\n",
                command=command,
            ),
        )
        if not self._confirm_and_warn(
            command, require_confirmation, requires_user_input
        ):
            return tr("❌ Command execution cancelled by user.")
        from janito.agent.platform_discovery import PlatformDiscovery

        pd = PlatformDiscovery()
        shell_exe = "powershell.exe" if pd.is_windows() else "pwsh"
        try:
            if runtime_config.get("all_out"):
                process = self._launch_process(shell_exe, command_with_encoding)
                return self._handle_all_out(process, timeout)
            else:
                process = self._launch_process(shell_exe, command_with_encoding)
                return self._handle_file_out(process, timeout)
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error running command: {error}", error=e)

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
