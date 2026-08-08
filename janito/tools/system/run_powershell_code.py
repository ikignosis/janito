#!/usr/bin/env python3
"""
Run PowerShell Code Tool - A class-based tool for executing PowerShell commands and scripts.

This tool demonstrates how to use the base tool class with progress reporting
for system command execution.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.run_powershell_code [args]
For AI function calling, use through the tool registry (tooling.tools_registry).

WARNING: This tool executes system commands and should be used with caution.
Only execute trusted code and be aware of security implications.
"""

import json
import os
import shutil
import subprocess
import sys
from typing import Any

from ...tooling import BaseTool, format_duration_ms, norm_path
from ...tooling.decorator import tool
from ._streaming import stream_execute

# Candidate executable names, in order of preference.
# 'pwsh' is PowerShell Core 6+/7+ (modern, cross-platform) and is preferred;
# 'powershell' is Windows PowerShell 5.1 (built into Windows, legacy).
_POWERSHELL_CANDIDATES = ("pwsh", "pwsh.exe", "powershell", "powershell.exe")


def _well_known_powershell_paths() -> list[str]:
    """
    Build a list of well-known PowerShell Core install locations.

    These are probed as a fallback when no PowerShell executable is found
    on PATH. Only existing paths are relevant; non-existent ones are skipped.
    """
    paths = []

    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get(
            "ProgramFiles(x86)", r"C:\Program Files (x86)"
        )
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        paths.extend(
            [
                os.path.join(program_files, "PowerShell", "7", "pwsh.exe"),
                os.path.join(program_files_x86, "PowerShell", "7", "pwsh.exe"),
            ]
        )
        if local_app_data:
            paths.append(
                os.path.join(local_app_data, "Programs", "PowerShell", "7", "pwsh.exe")
            )
    elif sys.platform == "darwin":
        paths.extend(
            [
                "/usr/local/bin/pwsh",  # Homebrew (Intel) / pkg installer symlink
                "/opt/homebrew/bin/pwsh",  # Homebrew (Apple Silicon)
                "/usr/local/microsoft/powershell/7/pwsh",  # pkg installer payload
            ]
        )
    else:  # Linux and other POSIX
        paths.extend(
            [
                "/usr/bin/pwsh",
                "/usr/local/bin/pwsh",
                "/opt/microsoft/powershell/7/pwsh",
                "/snap/bin/pwsh",
            ]
        )

    return paths


@tool(permissions="x")
class RunPowerShellCode(BaseTool):
    """
    Tool for executing PowerShell commands and scripts.

    This tool runs PowerShell code and returns the output, errors, and exit code.
    It supports both single commands and multi-line scripts.

    The tool automatically detects the best available PowerShell executable,
    preferring PowerShell Core (pwsh, 6+/7+) and falling back to Windows
    PowerShell 5.1 (powershell). Detection results are cached for the
    lifetime of the process.

    Security Notes:
    - Only execute trusted PowerShell code
    - Be cautious with scripts that modify system state
    - Consider using -WhatIf parameter for potentially destructive operations
    """

    # Cached result of executable detection (None = not found or not checked yet)
    _powershell_path: str | None = None
    _powershell_checked: bool = False

    @classmethod
    def _find_powershell(cls) -> str | None:
        """
        Locate the best available PowerShell executable.

        PowerShell Core (pwsh) is preferred over legacy Windows PowerShell
        (powershell). The search checks PATH first, then well-known install
        locations. The result is cached on the class for subsequent calls.

        Returns:
            Optional[str]: Absolute path to the executable, or None if not found
        """
        if cls._powershell_checked:
            return cls._powershell_path
        cls._powershell_checked = True
        cls._powershell_path = None

        # 1) Search PATH (prefers pwsh over powershell)
        for name in _POWERSHELL_CANDIDATES:
            path = shutil.which(name)
            if path:
                cls._powershell_path = path
                return path

        # 2) Probe well-known install locations (PowerShell Core only)
        for path in _well_known_powershell_paths():
            if os.path.isfile(path) and os.access(path, os.X_OK):
                cls._powershell_path = path
                return path

        return None

    @classmethod
    def should_load(cls) -> bool:
        """
        Only load this tool if a PowerShell executable is available.

        Returns:
            bool: True if PowerShell Core (pwsh) or Windows PowerShell
                (powershell) is found, False otherwise
        """
        if cls._find_powershell() is None:
            cls._load_skip_reason = (
                "no PowerShell executable found (looked for 'pwsh' and "
                "'powershell' on PATH and in well-known install locations)"
            )
            return False
        return True

    def run(
        self,
        code: str,
        working_directory: str | None = None,
        timeout: int | None = 60,
        capture_output: bool = True,
        capture_errors: bool = True,
    ) -> dict[str, Any]:
        """
        Execute PowerShell code and return results.

        Args:
            code (str): PowerShell code to execute (can be single command or multi-line script)
            working_directory (Optional[str]): Working directory for execution (default: current directory)
            timeout (Optional[int]): Maximum execution time in seconds (default: 60, None for no limit)
            capture_output (bool): Whether to capture standard output (default: True)
            capture_errors (bool): Whether to capture standard error (default: True)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if execution succeeded (exit code 0)
                - 'exit_code': integer exit code from PowerShell
                - 'stdout': captured standard output (if capture_output=True)
                - 'stderr': captured standard error (if capture_errors=True)
                - 'command': the PowerShell command that was executed
                - 'powershell_executable': path of the PowerShell executable used
                - 'working_directory': the working directory used
                - 'execution_time_ms': execution time in milliseconds
                - 'error': error message if execution failed (only present if success=False)

        Example:
            >>> tool = RunPowerShellCode()
            >>> result = tool.run(code="Get-Process | Select-Object -First 5")
            >>> print(result['stdout'])
        """
        import time

        start_time = time.time()

        powershell_path = self._find_powershell()
        if powershell_path is None:
            self.report_error("PowerShell not found")
            return {
                "success": False,
                "error": (
                    "No PowerShell executable found. Install PowerShell Core "
                    "(pwsh) or ensure Windows PowerShell (powershell) is on PATH."
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
                        f"Working directory does not exist: "
                        f"{os.path.abspath(working_directory)}"
                    ),
                    "exit_code": -1,
                    "working_directory": working_directory,
                }

            norm_working_dir = norm_path(abs_working_dir)
            self._report_exec_start(code, norm_working_dir)
            ps_command = self._build_command(powershell_path, code)

            exit_code, stdout_lines, stderr_lines, execution_time_ms = stream_execute(
                ps_command,
                abs_working_dir,
                capture_output,
                capture_errors,
                timeout,
                start_time,
                self.report_output,
                report_blank_first=True,
            )

            return self._build_result(
                exit_code,
                code,
                powershell_path,
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
                "error": f"PowerShell execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms,
            }
        except FileNotFoundError:
            self.report_error("PowerShell not found")
            return {
                "success": False,
                "error": (
                    f"PowerShell executable not found: {powershell_path}. "
                    "Install PowerShell Core (pwsh) or ensure Windows "
                    "PowerShell (powershell) is available."
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
                "error": f"Failed to execute PowerShell: {e!s}",
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

    def _build_command(self, powershell_path: str, code: str) -> list[str]:
        """Build the PowerShell argv, forcing UTF-8 console encoding."""
        # Wrapped in try/catch: setting console encodings can fail when
        # stdin/stdout are redirected (common with pwsh on non-Windows),
        # and must never abort the user's script.
        encoding_prefix = (
            "try { $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}; "
            "try { $InputEncoding = [Console]::InputEncoding = [System.Text.Encoding]::UTF8 } catch {}; "
        )
        code_with_encoding = encoding_prefix + code

        # -NoProfile for faster execution, -NonInteractive to never block on
        # prompts. -ExecutionPolicy only exists on Windows.
        ps_command = [powershell_path, "-NoProfile", "-NonInteractive"]
        if os.name == "nt":
            ps_command += ["-ExecutionPolicy", "Bypass"]
        ps_command += ["-Command", code_with_encoding]
        return ps_command

    def _report_exec_start(self, code: str, norm_working_dir: str) -> None:
        """Report the code to be executed."""
        code_preview = code
        if len(code) > 200:
            code_preview = code[:200] + "..."
        self.report_start(
            f"⚙️ Executing PowerShell code in {norm_working_dir}:\n{code_preview}"
        )

    def _build_result(
        self,
        exit_code: int,
        code: str,
        powershell_path: str,
        working_directory: str | None,
        abs_working_dir: str,
        stdout_lines: list[str],
        stderr_lines: list[str],
        capture_output: bool,
        capture_errors: bool,
        execution_time_ms: int,
    ) -> dict[str, Any]:
        """Assemble the result dict and report the outcome."""
        success = exit_code == 0
        stdout_text = "".join(stdout_lines) if stdout_lines else ""
        stderr_text = "".join(stderr_lines) if stderr_lines else ""
        output_result = {
            "success": success,
            "exit_code": exit_code,
            "command": code,
            "powershell_executable": powershell_path,
            "working_directory": working_directory or abs_working_dir,
            "execution_time_ms": execution_time_ms,
        }
        if capture_output:
            output_result["stdout"] = stdout_text
        if capture_errors:
            output_result["stderr"] = stderr_text
        if success:
            self._report_success(execution_time_ms, capture_output, stdout_text)
        else:
            self._report_failure(exit_code, capture_errors, stderr_text)
            output_result[
                "error"
            ] = f"PowerShell execution failed with exit code {exit_code}"
        return output_result

    def _report_success(
        self,
        execution_time_ms: int,
        capture_output: bool,
        stdout_text: str,
    ) -> None:
        """Report a successful execution summary."""
        output_summary = f"Completed in {format_duration_ms(execution_time_ms)}"
        if capture_output and stdout_text:
            lines = stdout_text.strip().split("\n")
            if lines:
                output_summary += f" ({len(lines)} lines output)"
        self.report_result(output_summary)

    def _report_failure(
        self,
        exit_code: int,
        capture_errors: bool,
        stderr_text: str,
    ) -> None:
        """Report a failed execution, truncating long stderr previews."""
        error_msg = f"Exit code {exit_code}"
        if capture_errors and stderr_text:
            stderr_preview = stderr_text[:100].replace("\n", " ")
            if len(stderr_text) > 100:
                stderr_preview += "..."
            error_msg += f": {stderr_preview}"
        self.report_error(error_msg)


# CLI interface for testing
def main():
    """Command line interface for testing the RunPowerShellCode tool."""
    parser = _build_parser()
    args = parser.parse_args()
    code = _read_code(args, parser)
    if code is None:
        return 1

    tool_instance = RunPowerShellCode()
    result = tool_instance.run(
        code=code,
        working_directory=args.directory,
        timeout=args.timeout,
        capture_output=not args.no_capture_output,
        capture_errors=not args.no_capture_errors,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_result(result, args)
    return 0 if result["success"] else 1


def _build_parser():
    """Build the CLI argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute PowerShell code for AI function calling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c "Get-Process | Select-Object -First 5"
  %(prog)s -c "Get-ChildItem -Recurse | Measure-Object" -d "C:\\Users"
  %(prog)s -c "Write-Host 'Hello World'" --json
  %(prog)s -f script.ps1
        """,
    )

    parser.add_argument("-c", "--code", help="PowerShell code to execute")
    parser.add_argument("-f", "--file", help="File containing PowerShell code")
    parser.add_argument("-d", "--directory", help="Working directory for execution")
    parser.add_argument(
        "-t", "--timeout", type=int, default=60, help="Timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--no-capture-output", action="store_true", help="Don't capture standard output"
    )
    parser.add_argument(
        "--no-capture-errors", action="store_true", help="Don't capture standard error"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )
    return parser


def _read_code(args, parser) -> str | None:
    """Resolve the code from --code/--file; return None on file errors."""
    if not args.code and not args.file:
        parser.error("Either --code or --file must be specified")

    if args.code and args.file:
        parser.error("Cannot specify both --code and --file")

    code = args.code
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            return None
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    return code


def _print_result(result: dict[str, Any], args) -> None:
    """Pretty-print the tool result."""
    if result["success"]:
        print(f"✓ PowerShell execution successful (exit code {result['exit_code']})")
        print(f"  Working directory: {norm_path(result['working_directory'])}")
        print(f"  Execution time: {format_duration_ms(result['execution_time_ms'])}")

        if args.verbose:
            print(f"  Executable: {result.get('powershell_executable', 'unknown')}")
            print("\nCommand:")
            print(f"  {result['command']}")

        if result.get("stdout"):
            print("\nOutput:")
            print(result["stdout"])

        if result.get("stderr"):
            print("\nStderr:")
            print(result["stderr"])
    else:
        print("✗ PowerShell execution failed")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        print(f"  Exit code: {result['exit_code']}")

        if args.verbose:
            print("\nCommand:")
            print(f"  {result['command']}")

        if result.get("stdout"):
            print("\nOutput:")
            print(result["stdout"])

        if result.get("stderr"):
            print("\nStderr:")
            print(result["stderr"])


if __name__ == "__main__":
    exit(main())
