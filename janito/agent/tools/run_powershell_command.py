from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import subprocess
import tempfile
import threading


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
        interactive (bool, optional): If True, warns that the command may require user interaction. Defaults to False. Non-interactive commands are preferred for automation and reliability.
    Returns:
        str: Output and status message, or file paths/line counts if output is large.
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
        encoding_prefix = "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        command_with_encoding = encoding_prefix + command
        self.report_info(
            tr("🖥️ Running PowerShell command: {command} ...\n", command=command)
        )
        if interactive:
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
                return tr("❌ Command execution cancelled by user.")
        from janito.agent.platform_discovery import is_windows

        shell_exe = "powershell.exe" if is_windows() else "pwsh"
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
                process = subprocess.Popen(
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
                )

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
                try:
                    return_code = process.wait(timeout=timeout)
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
                stdout_file.flush()
                stderr_file.flush()

                self.report_success(
                    tr(" ✅ return code {return_code}", return_code=return_code)
                )
                warning_msg = ""
                if interactive:
                    warning_msg = tr(
                        "⚠️  Warning: This command might be interactive, require user input, and might hang.\n"
                    )
                # Read back the content for summary if not too large
                with open(
                    stdout_file.name, "r", encoding="utf-8", errors="replace"
                ) as out_f:
                    stdout_content = out_f.read()
                with open(
                    stderr_file.name, "r", encoding="utf-8", errors="replace"
                ) as err_f:
                    stderr_content = err_f.read()
                max_lines = 100
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
                        "returncode: {return_code}\nUse the get_lines tool to inspect the contents of these files when needed.",
                        return_code=return_code,
                    )
                    return result
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error running command: {error}", error=e)
