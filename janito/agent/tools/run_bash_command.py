from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

import subprocess
import tempfile
import sys

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
    def call(self, command: str, timeout: int = 60, require_confirmation: bool = False, interactive: bool = False) -> str:
        """
        Execute a bash command and capture live output.

        Args:
            command (str): The bash command to execute.
            timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
            require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
            interactive (bool, optional): If True, warns that the command may require user interaction. Defaults to False.

        Returns:
            str: Output and status message.
        """
        """
        Execute a bash command and capture live output.

        Args:
            command (str): The bash command to execute.
            timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
            require_confirmation (bool, optional): If True, require user confirmation before running. Defaults to False.
            interactive (bool, optional): If True, warns that the command may require user interaction. Defaults to False.

        Returns:
            str: Output and status message.
        """
        if not command.strip():
            self.report_warning("⚠️ Warning: Empty command provided. Operation skipped.")
            return "Warning: Empty command provided. Operation skipped."
        self.report_info(f"🖥️  Running bash command: {command}\n")
        if interactive:
            self.report_info("⚠️  Warning: This command might be interactive, require user input, and might hang.")

            sys.stdout.flush()

        try:
            with tempfile.NamedTemporaryFile(mode='w+', prefix='run_bash_stdout_', delete=False, encoding='utf-8') as stdout_file, \
                 tempfile.NamedTemporaryFile(mode='w+', prefix='run_bash_stderr_', delete=False, encoding='utf-8') as stderr_file:
                # Use bash explicitly for command execution
                process = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True
                )
                try:
                    return_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.report_error(f" ❌ Timed out after {timeout} seconds.")
                    return f"Command timed out after {timeout} seconds."

                # Print live output to user
                stdout_file.flush()
                stderr_file.flush()
                with open(stdout_file.name, 'r', encoding='utf-8') as out_f:
                    out_f.seek(0)
                    for line in out_f:
                        self.report_stdout(line)
                with open(stderr_file.name, 'r', encoding='utf-8') as err_f:
                    err_f.seek(0)
                    for line in err_f:
                        self.report_stderr(line)

                # Count lines
                with open(stdout_file.name, 'r', encoding='utf-8') as out_f:
                    stdout_lines = sum(1 for _ in out_f)
                with open(stderr_file.name, 'r', encoding='utf-8') as err_f:
                    stderr_lines = sum(1 for _ in err_f)

                self.report_success(f" ✅ return code {return_code}")
                warning_msg = ""
                if interactive:
                    warning_msg = "⚠️  Warning: This command might be interactive, require user input, and might hang.\n"
                return (
                    warning_msg +
                    f"stdout_file: {stdout_file.name} (lines: {stdout_lines})\n"
                    f"stderr_file: {stderr_file.name} (lines: {stderr_lines})\n"
                    f"returncode: {return_code}\n"
                    f"Use the get_lines tool to inspect the contents of these files when needed."
                )
        except Exception as e:
            self.report_error(f" ❌ Error: {e}")
            return f"Error running command: {e}"

