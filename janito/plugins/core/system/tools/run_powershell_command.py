from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.i18n import tr
import subprocess
import os
from janito.tools.path_utils import expand_path
import tempfile
import threading


@register_local_tool
class RunPowershellCommandTool(ToolBase):
    """
    Execute a non-interactive command using the PowerShell shell and capture live output.
    This tool explicitly invokes 'powershell.exe' (on Windows) or 'pwsh' (on other platforms if available).
    All commands are automatically prepended with UTF-8 output encoding:
    $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
    For file output, it is recommended to use -Encoding utf8 in your PowerShell commands (e.g., Out-File -Encoding utf8) to ensure correct file encoding.

    Args:
        command (str): The PowerShell command to execute. This string is passed directly to PowerShell using the --Command argument (not as a script file).
        timeout (int): Timeout in seconds for the command. Defaults to 60.
        require_confirmation (bool): If True, require user confirmation before running. Defaults to False.
        requires_user_input (bool): If True, warns that the command may require user input and might hang. Defaults to False. Non-interactive commands are preferred for automation and reliability.
        silent (bool): If True, suppresses progress and status messages. Defaults to False.

    Returns:
        str: Output and status message, or file paths/line counts if output is large.
    """

    permissions = ToolPermissions(execute=True)
    tool_name = "run_powershell_command"

    def _confirm_and_warn(self, command, require_confirmation, requires_user_input):
        if requires_user_input:
            self.report_warning(
                tr(
                    "⚠️  Warning: This command might be interactive, require user input, and might hang."
                ),
                ReportAction.EXECUTE,
            )
        if require_confirmation:
            self.report_warning(
                tr("⚠️ Confirmation requested, but no handler (auto-confirmed)."),
                ReportAction.EXECUTE,
            )
            return True  # Auto-confirm for now
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

    def _stream_output(self, stream, file_obj, report_func, count_func, counter):
        for line in stream:
            file_obj.write(line)
            file_obj.flush()
            report_func(line.rstrip("\r\n"), ReportAction.EXECUTE)
            if count_func == "stdout":
                counter["stdout"] += 1
            else:
                counter["stderr"] += 1

    def _format_result(
        self, requires_user_input, return_code, stdout_file, stderr_file, max_lines=100
    ):
        warning_msg = ""
        if requires_user_input:
            warning_msg = tr(
                "⚠️  Warning: This command might be interactive, require user input, and might hang.\n"
            )
        with open(stdout_file.name, "r", encoding="utf-8", errors="replace") as out_f:
            stdout_content = out_f.read()
        with open(stderr_file.name, "r", encoding="utf-8", errors="replace") as err_f:
            stderr_content = err_f.read()
        stdout_lines = stdout_content.count("\n")
        stderr_lines = stderr_content.count("\n")
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
                "stdout_file: {stdout_file} (lines: {stdout_lines})\n",
                stdout_file=stdout_file.name,
                stdout_lines=stdout_lines,
            )
            if stderr_lines > 0 and stderr_content.strip():
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
        encoding_prefix = "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        command_with_encoding = encoding_prefix + command
        if not silent:
            self.report_action(
                tr("🖥️ Running PowerShell command: {command} ...\n", command=command),
                ReportAction.EXECUTE,
            )
        else:
            self.report_action(tr("⚡ Executing..."), ReportAction.EXECUTE)
        self._confirm_and_warn(command, require_confirmation, requires_user_input)
        from janito.platform_discovery import PlatformDiscovery

        pd = PlatformDiscovery()
        shell_exe = "powershell.exe" if pd.is_windows() else "pwsh"
        try:
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
                process = self._launch_process(shell_exe, command_with_encoding)
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
                        tr(" ✅ return code {return_code}", return_code=return_code),
                        ReportAction.EXECUTE,
                    )
                return self._format_result(
                    requires_user_input, return_code, stdout_file, stderr_file
                )
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e), ReportAction.EXECUTE)
            return tr("Error running command: {error}", error=e)
