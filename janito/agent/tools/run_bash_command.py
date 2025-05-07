from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
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
        requires_user_input (bool, optional): If True, warns that the command may require user input and might hang. Defaults to False. Non-interactive commands are preferred for automation and reliability.
    Returns:
        str: File paths and line counts for stdout and stderr.
    """

    def run(
        self,
        command: str,
        timeout: int = 60,
        require_confirmation: bool = False,
        requires_user_input: bool = False,
    ) -> str:
        if not command.strip():
            self.report_warning(tr("\u2139\ufe0f Empty command provided."))
            return tr("Warning: Empty command provided. Operation skipped.")
        self.report_info(
            ActionType.EXECUTE,
            tr("🖥️ Run bash command: {command} ...\n", command=command),
        )
        if requires_user_input:
            self.report_warning(
                tr(
                    "\u26a0\ufe0f  Warning: This command might be interactive, require user input, and might hang."
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
                try:
                    stdout_content, stderr_content = process.communicate(
                        timeout=timeout
                    )
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.report_error(
                        tr(
                            " \u274c Timed out after {timeout} seconds.",
                            timeout=timeout,
                        )
                    )
                    return tr(
                        "Command timed out after {timeout} seconds.", timeout=timeout
                    )
                self.report_success(
                    tr(
                        " \u2705 return code {return_code}",
                        return_code=process.returncode,
                    )
                )
                warning_msg = ""
                if requires_user_input:
                    warning_msg = tr(
                        "\u26a0\ufe0f  Warning: This command might be interactive, require user input, and might hang.\n"
                    )
                max_lines = 100
                stdout_lines = stdout_content.count("\n")
                stderr_lines = stderr_content.count("\n")
                if stdout_lines <= max_lines and stderr_lines <= max_lines:
                    result = warning_msg + tr(
                        "Return code: {return_code}\n--- STDOUT ---\n{stdout_content}",
                        return_code=process.returncode,
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
                        "returncode: {return_code}\nUse the get_lines tool to inspect the contents of these files when needed.",
                        return_code=process.returncode,
                    )
                    return result
        except Exception as e:
            self.report_error(tr(" \u274c Error: {error}", error=e))
            return tr("Error running command: {error}", error=e)
