#!/usr/bin/env python3
"""
Run Python File Tool - A class-based tool for executing Python script files.

This tool demonstrates how to use the base tool class with progress reporting
for system command execution.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.run_python_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).

WARNING: This tool executes system commands and should be used with caution.
Only execute trusted code and be aware of security implications.
"""

import json
import os
import subprocess
import sys
from typing import Any

from ...tooling import BaseTool, format_duration_ms, norm_path
from ...tooling.decorator import tool
from ._streaming import lines_to_text, preview_lines, stream_execute


@tool(permissions="x")
class RunPythonFile(BaseTool):
    """
    Tool for executing Python script files.

    This tool runs Python files and returns the output, errors, and exit code.
    It executes files using 'python filename' rather than passing code via -c.

    Security Notes:
    - Only execute trusted Python files
    - Be cautious with scripts that modify system state
    - Consider the security implications of arbitrary file execution
    """

    def run(
        self,
        file_path: str,
        working_directory: str | None = None,
        timeout: int | None = 60,
        capture_output: bool = True,
        capture_errors: bool = True,
        python_executable: str | None = None,
        additional_args: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute Python file and return results.

        Args:
            file_path (str): Path to the Python file to execute
            working_directory (Optional[str]): Working directory for execution (default: current directory)
            timeout (Optional[int]): Maximum execution time in seconds (default: 60, None for no limit)
            capture_output (bool): Whether to capture standard output (default: True)
            capture_errors (bool): Whether to capture standard error (default: True)
            python_executable (Optional[str]): Path to Python executable (default: current Python interpreter)
            additional_args (Optional[List[str]]): Additional command-line arguments to pass to the script

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if execution succeeded (exit code 0)
                - 'exit_code': integer exit code from Python
                - 'stdout': captured standard output (if capture_output=True)
                - 'stderr': captured standard error (if capture_errors=True)
                - 'command': the full command that was executed
                - 'file_path': the Python file that was executed
                - 'working_directory': the working directory used
                - 'execution_time_ms': execution time in milliseconds
                - 'error': error message if execution failed (only present if success=False)

        Example:
            >>> tool = RunPythonFile()
            >>> result = tool.run(file_path="script.py", additional_args=["arg1", "arg2"])
            >>> print(result['stdout'])
        """
        import time

        start_time = time.time()

        try:
            abs_file_path = self._resolve_file_path(file_path)
            if abs_file_path is None:
                return {
                    "success": False,
                    "error": f"Python file does not exist: {file_path}",
                    "exit_code": -1,
                    "file_path": file_path,
                }

            abs_working_dir = self._resolve_working_dir(
                working_directory, abs_file_path
            )
            if abs_working_dir is None:
                return {
                    "success": False,
                    "error": (
                        f"Working directory does not exist: {os.path.abspath(working_directory)}"
                    ),
                    "exit_code": -1,
                    "file_path": file_path,
                    "working_directory": working_directory,
                }

            python_executable = python_executable or sys.executable
            python_command = self._build_command(
                python_executable, abs_file_path, additional_args
            )
            self._report_exec_start(
                python_command,
                norm_path(abs_file_path),
                norm_path(abs_working_dir),
            )

            exit_code, stdout_lines, stderr_lines, execution_time_ms = stream_execute(
                python_command,
                abs_working_dir,
                capture_output,
                capture_errors,
                timeout,
                start_time,
                self.report_output,
            )

            return self._build_result(
                exit_code,
                python_command,
                file_path,
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
                "error": f"Python file execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": " ".join(python_command)
                if "python_command" in locals()
                else "",
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms,
            }
        except FileNotFoundError:
            self.report_error("Python executable not found")
            return {
                "success": False,
                "error": f"Python executable not found: {python_executable}",
                "exit_code": -1,
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to execute Python file: {e!s}",
                "exit_code": -1,
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms,
            }

    def _resolve_file_path(self, file_path: str) -> str | None:
        """Return the absolute file path, or None when it does not exist."""
        if not os.path.exists(file_path):
            return None
        return os.path.abspath(file_path)

    def _resolve_working_dir(
        self, working_directory: str | None, abs_file_path: str
    ) -> str | None:
        """Return the absolute working dir, or None when it does not exist."""
        if working_directory:
            abs_working_dir = os.path.abspath(working_directory)
            if not os.path.exists(abs_working_dir):
                return None
            return abs_working_dir
        return os.path.dirname(abs_file_path)

    def _build_command(
        self,
        python_executable: str,
        abs_file_path: str,
        additional_args: list[str] | None,
    ) -> list[str]:
        """Build the python argv list."""
        python_command = [python_executable, abs_file_path]
        if additional_args:
            python_command.extend(additional_args)
        return python_command

    def _report_exec_start(
        self,
        python_command: list[str],
        norm_file_path: str,
        norm_working_dir: str,
    ) -> None:
        """Report the file to be executed."""
        cmd_parts = [python_command[0], norm_file_path]
        if len(python_command) > 2:
            cmd_parts.extend(python_command[2:])
        command_preview = " ".join(cmd_parts)
        if len(command_preview) > 200:
            command_preview = command_preview[:200] + "..."
        self.report_start(
            f"🐍 Executing Python file in {norm_working_dir}:\n{command_preview}"
        )

    def _build_result(
        self,
        exit_code: int,
        python_command: list[str],
        file_path: str,
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
            "command": " ".join(python_command),
            "file_path": file_path,
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
            output_result[
                "error"
            ] = f"Python file execution failed with exit code {exit_code}"
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


# CLI interface for testing
def main():
    """Command line interface for testing the RunPythonFile tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute Python file for AI function calling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s script.py
  %(prog)s -f my_script.py -d "C:\\Users" -- arg1 arg2
  %(prog)s test_script.py --json
        """,
    )

    parser.add_argument("file", help="Python file to execute")
    parser.add_argument("-d", "--directory", help="Working directory for execution")
    parser.add_argument(
        "-p", "--python", help="Python executable to use (default: current interpreter)"
    )
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
    parser.add_argument(
        "--",
        dest="additional_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to the Python script",
    )

    args = parser.parse_args()

    # Create tool instance and execute
    tool_instance = RunPythonFile()
    result = tool_instance.run(
        file_path=args.file,
        working_directory=args.directory,
        timeout=args.timeout,
        capture_output=not args.no_capture_output,
        capture_errors=not args.no_capture_errors,
        python_executable=args.python,
        additional_args=args.additional_args,
    )

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(
                f"? Python file execution successful (exit code {result['exit_code']})"
            )
            print(f"  File: {norm_path(result['file_path'])}")
            print(f"  Working directory: {norm_path(result['working_directory'])}")
            print(
                f"  Execution time: {format_duration_ms(result['execution_time_ms'])}"
            )

            if args.verbose:
                print("\nCommand:")
                print(f"  {result['command']}")

            if result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])

            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])

        else:
            print("? Python file execution failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Exit code: {result['exit_code']}")
            print(f"  File: {norm_path(result['file_path'])}")

            if args.verbose:
                print("\nCommand:")
                print(f"  {result['command']}")

            if result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])

            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
