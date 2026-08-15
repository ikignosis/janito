#!/usr/bin/env python3
"""
Run Bash Code Tool - A class-based tool for executing Bash commands and scripts.

This tool demonstrates how to use the base tool class with progress reporting
for system command execution.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.run_bash_code [args]
For AI function calling, use through the tool registry (tooling.tools_registry).

WARNING: This tool executes system commands and should be used with caution.
Only execute trusted code and be aware of security implications.
"""

import os
import shutil
import subprocess
import sys
from typing import Any

from ...tooling import BaseTool, format_duration_ms, norm_path
from ...tooling.decorator import tool
from ._streaming import lines_to_text, preview_lines, stream_execute

# Candidate executable names, in order of preference.
# 'bash' is the Bourne Again SHell (full-featured) and is preferred;
# 'sh' is the POSIX shell fallback (dash/ash on minimal systems) for
# environments where bash is not installed.
_BASH_CANDIDATES = ("bash", "bash.exe")
_SH_FALLBACK_CANDIDATES = ("sh", "sh.exe")


def _well_known_bash_paths() -> list[str]:
    """
    Build a list of well-known Bash install locations.

    These are probed as a fallback when no Bash executable is found
    on PATH. Only existing paths are relevant; non-existent ones are skipped.
    """
    paths = []

    if os.name == "nt":
        # Git Bash and WSL locations on Windows
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)", r"C:\Program Files (x86)"
        )
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        paths.extend(
            [
                os.path.join(program_files, "Git", "bin", "bash.exe"),
                os.path.join(program_files, "Git", "usr", "bin", "bash.exe"),
                os.path.join(program_files_x86, "Git", "bin", "bash.exe"),
                os.path.join(system_root, "System32", "bash.exe"),  # WSL launcher
            ]
        )
        if local_app_data:
            paths.append(
                os.path.join(local_app_data, "Programs", "Git", "bin", "bash.exe")
            )
    elif sys.platform == "darwin":
        paths.extend(
            [
                "/bin/bash",  # System bash (3.2, always present)
                "/usr/local/bin/bash",  # Homebrew (Intel)
                "/opt/homebrew/bin/bash",  # Homebrew (Apple Silicon)
                "/opt/local/bin/bash",  # MacPorts
            ]
        )
    else:  # Linux and other POSIX
        paths.extend(
            [
                "/bin/bash",
                "/usr/bin/bash",
                "/usr/local/bin/bash",
                "/data/data/com.termux/files/usr/bin/bash",  # Termux (Android)
            ]
        )

    return paths


def _well_known_sh_paths() -> list[str]:
    """Well-known POSIX sh locations, probed only when bash is unavailable."""
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        return [os.path.join(program_files, "Git", "usr", "bin", "sh.exe")]
    return ["/bin/sh", "/usr/bin/sh"]


@tool(permissions="x")
class RunBashCode(BaseTool):
    """
    Tool for executing Bash commands and scripts.

    This tool runs Bash code and returns the output, errors, and exit code.
    It supports both single commands and multi-line scripts, including
    pipelines, redirections, loops, and standard shell constructs.

    The tool automatically detects the best available shell executable,
    preferring Bash and falling back to the POSIX shell (sh) on minimal
    systems. Detection results are cached for the lifetime of the process.

    Security Notes:
    - Only execute trusted shell code
    - Be cautious with scripts that modify system state
    - Consider dry-run flags (e.g. rm -i, --dry-run) for destructive operations
    """

    # Cached result of executable detection (None = not found or not checked yet)
    _shell_path: str | None = None
    _shell_checked: bool = False

    @classmethod
    def _find_shell(cls) -> str | None:
        """
        Locate the best available shell executable.

        Bash is preferred over the POSIX shell (sh). The search checks PATH
        first, then well-known install locations. The result is cached on
        the class for subsequent calls.

        Returns:
            Optional[str]: Absolute path to the executable, or None if not found
        """
        if cls._shell_checked:
            return cls._shell_path
        cls._shell_checked = True
        cls._shell_path = None

        # 1) Search PATH (prefers bash over sh)
        for name in _BASH_CANDIDATES:
            path = shutil.which(name)
            if path:
                cls._shell_path = path
                return path

        # 2) Probe well-known bash install locations
        for path in _well_known_bash_paths():
            if os.path.isfile(path) and os.access(path, os.X_OK):
                cls._shell_path = path
                return path

        # 3) Fall back to POSIX sh on PATH, then well-known locations
        for name in _SH_FALLBACK_CANDIDATES:
            path = shutil.which(name)
            if path:
                cls._shell_path = path
                return path

        for path in _well_known_sh_paths():
            if os.path.isfile(path) and os.access(path, os.X_OK):
                cls._shell_path = path
                return path

        return None

    @classmethod
    def should_load(cls) -> bool:
        """
        Only load this tool if a Bash (or POSIX sh) executable is available.

        Returns:
            bool: True if Bash (bash) or a POSIX shell (sh) is found,
                False otherwise
        """
        if cls._find_shell() is None:
            cls._load_skip_reason = (
                "no Bash executable found (looked for 'bash' and 'sh' on "
                "PATH and in well-known install locations)"
            )
            return False
        return True

    @staticmethod
    def _is_bash(executable_path: str) -> bool:
        """Check whether the resolved executable is bash (vs. a plain sh)."""
        return "bash" in os.path.basename(executable_path).lower()

    def run(
        self,
        code: str,
        working_directory: str | None = None,
        timeout: int | None = 60,
        capture_output: bool = True,
        capture_errors: bool = True,
        bash_executable: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute Bash code and return results.

        Args:
            code (str): Bash code to execute (can be single command or multi-line script)
            working_directory (Optional[str]): Working directory for execution (default: current directory)
            timeout (Optional[int]): Maximum execution time in seconds (default: 60, None for no limit)
            capture_output (bool): Whether to capture standard output (default: True)
            capture_errors (bool): Whether to capture standard error (default: True)
            bash_executable (Optional[str]): Path to shell executable (default: auto-detected bash, falling back to sh)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if execution succeeded (exit code 0)
                - 'exit_code': integer exit code from the shell
                - 'stdout': captured standard output (if capture_output=True)
                - 'stderr': captured standard error (if capture_errors=True)
                - 'command': the Bash code that was executed
                - 'bash_executable': path of the shell executable used
                - 'working_directory': the working directory used
                - 'execution_time_ms': execution time in milliseconds
                - 'error': error message if execution failed (only present if success=False)

        Example:
            >>> tool = RunBashCode()
            >>> result = tool.run(code="ls -la | head -5")
            >>> print(result['stdout'])
        """
        import time

        start_time = time.time()

        shell_path = bash_executable or self._find_shell()
        if shell_path is None:
            self.report_error("Bash not found")
            return {
                "success": False,
                "error": (
                    "No Bash executable found. Install bash or ensure a POSIX shell (sh) is on PATH."
                ),
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        try:
            abs_working_dir = self._resolve_working_dir(working_directory)
            if abs_working_dir is None:
                return {
                    "success": False,
                    "error": (
                        f"Working directory does not exist: {os.path.abspath(working_directory)}"
                    ),
                    "exit_code": -1,
                    "working_directory": working_directory,
                }

            norm_working_dir = norm_path(abs_working_dir)
            self._report_exec_start(code, norm_working_dir)
            shell_command = self._build_shell_command(shell_path, code)

            exit_code, stdout_lines, stderr_lines, execution_time_ms = stream_execute(
                shell_command,
                abs_working_dir,
                capture_output,
                capture_errors,
                timeout,
                start_time,
                self.report_output,
                report_blank_first=True,
                popen_kwargs={
                    "encoding": "utf-8",
                    "errors": "replace",
                    "env": {**os.environ, "BASH_ENV": "", "ENV": ""},
                },
            )

            return self._build_result(
                exit_code,
                code,
                shell_path,
                working_directory,
                abs_working_dir,
                stdout_lines,
                stderr_lines,
                capture_output,
                capture_errors,
                execution_time_ms,
            )
        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Timeout after {timeout}s")
            return {
                "success": False,
                "error": f"Bash execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms,
            }
        except FileNotFoundError:
            self.report_error("Bash not found")
            return {
                "success": False,
                "error": (
                    f"Shell executable not found: {shell_path}. Install bash or ensure a POSIX shell (sh) is available."
                ),
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to execute Bash: {e!s}",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms,
            }

    def _resolve_working_dir(self, working_directory: str | None) -> str | None:
        """Return the absolute working dir, or None when it does not exist."""
        if working_directory:
            abs_working_dir = os.path.abspath(working_directory)
            if not os.path.exists(abs_working_dir):
                return None
            return abs_working_dir
        return os.getcwd()

    def _report_exec_start(self, code: str, norm_working_dir: str) -> None:
        """Report the code to be executed."""
        code_preview = code
        if len(code) > 200:
            code_preview = code[:200] + "..."
        self.report_start(
            f"⚙️ Executing Bash code in {norm_working_dir}:\n{code_preview}"
        )

    def _build_shell_command(self, shell_path: str, code: str) -> list[str]:
        """Build the shell argv; bash gets --noprofile/--norc, sh does not."""
        if self._is_bash(shell_path):
            return [shell_path, "--noprofile", "--norc", "-c", code]
        return [shell_path, "-c", code]

    def _build_result(
        self,
        exit_code: int,
        code: str,
        shell_path: str,
        working_directory: str | None,
        abs_working_dir: str,
        stdout_lines: list[str],
        stderr_lines: list[str],
        capture_output: bool,
        capture_errors: bool,
        execution_time_ms: int,
    ) -> dict[str, Any]:
        """Assemble the result dict and report the outcome.

        stdout/stderr carry the full captured output inline.
        """
        success = exit_code == 0
        stdout_text = lines_to_text(stdout_lines) if capture_output else ""
        stderr_text = lines_to_text(stderr_lines) if capture_errors else ""
        output_result = {
            "success": success,
            "exit_code": exit_code,
            "command": code,
            "bash_executable": shell_path,
            "working_directory": working_directory or abs_working_dir,
            "execution_time_ms": execution_time_ms,
        }
        if capture_output:
            output_result["stdout"] = stdout_text
        if capture_errors:
            output_result["stderr"] = stderr_text
        if success:
            self._report_success(
                execution_time_ms, capture_output, stdout_lines, stderr_lines
            )
        else:
            self._report_failure(exit_code, capture_errors, stderr_lines, stdout_lines)
            output_result["error"] = f"Bash execution failed with exit code {exit_code}"
        return output_result

    def _report_success(
        self,
        execution_time_ms: int,
        capture_output: bool,
        stdout_lines: list[str],
        stderr_lines: list[str],
    ) -> None:
        """Report a successful execution summary."""
        output_summary = f"Completed in {format_duration_ms(execution_time_ms)}"
        if capture_output and stdout_lines:
            output_summary += f" ({len(stdout_lines)} lines output)"
        self.report_result(output_summary)

    def _report_failure(
        self,
        exit_code: int,
        capture_errors: bool,
        stderr_lines: list[str],
        stdout_lines: list[str],
    ) -> None:
        """Report a failed execution, truncating long stderr previews."""
        error_msg = f"Exit code {exit_code}"
        if capture_errors and stderr_lines:
            stderr_preview = preview_lines(stderr_lines, 100)
            error_msg += f": {stderr_preview}"
        self.report_error(error_msg)


# CLI interface for testing (shared harness)
def main() -> int:
    """Command line interface for testing the RunBashCode tool."""
    from ._exec_cli import run_cli

    return run_cli(
        RunBashCode,
        tool_name="Bash",
        description="Execute Bash code for AI function calling",
        epilog="""\
Examples:
  %(prog)s -c "ls -la | head -5"
  %(prog)s -c "for i in 1 2 3; do echo $i; done" -d "/tmp"
  %(prog)s -c "echo 'Hello World'" --json
  %(prog)s -f script.sh
        """,
        code_help="Bash code to execute",
        file_help="File containing Bash code",
        result_key="bash_executable",
        add_shell_arg=True,
        shell_help="Shell executable to use (default: auto-detected bash, falling back to sh)",
    )


if __name__ == "__main__":
    exit(main())
