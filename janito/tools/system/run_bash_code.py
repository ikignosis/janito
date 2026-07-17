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

import subprocess
import json
import os
import shutil
import sys
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool, norm_path
from ..decorator import tool


# Candidate executable names, in order of preference.
# 'bash' is the Bourne Again SHell (full-featured) and is preferred;
# 'sh' is the POSIX shell fallback (dash/ash on minimal systems) for
# environments where bash is not installed.
_BASH_CANDIDATES = ("bash", "bash.exe")
_SH_FALLBACK_CANDIDATES = ("sh", "sh.exe")


def _well_known_bash_paths() -> List[str]:
    """
    Build a list of well-known Bash install locations.

    These are probed as a fallback when no Bash executable is found
    on PATH. Only existing paths are relevant; non-existent ones are skipped.
    """
    paths = []

    if os.name == "nt":
        # Git Bash and WSL locations on Windows
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        paths.extend([
            os.path.join(program_files, "Git", "bin", "bash.exe"),
            os.path.join(program_files, "Git", "usr", "bin", "bash.exe"),
            os.path.join(program_files_x86, "Git", "bin", "bash.exe"),
            os.path.join(system_root, "System32", "bash.exe"),  # WSL launcher
        ])
        if local_app_data:
            paths.append(
                os.path.join(local_app_data, "Programs", "Git", "bin", "bash.exe")
            )
    elif sys.platform == "darwin":
        paths.extend([
            "/bin/bash",                          # System bash (3.2, always present)
            "/usr/local/bin/bash",                # Homebrew (Intel)
            "/opt/homebrew/bin/bash",             # Homebrew (Apple Silicon)
            "/opt/local/bin/bash",                # MacPorts
        ])
    else:  # Linux and other POSIX
        paths.extend([
            "/bin/bash",
            "/usr/bin/bash",
            "/usr/local/bin/bash",
            "/data/data/com.termux/files/usr/bin/bash",  # Termux (Android)
        ])

    return paths


def _well_known_sh_paths() -> List[str]:
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
    _shell_path: Optional[str] = None
    _shell_checked: bool = False

    @classmethod
    def _find_shell(cls) -> Optional[str]:
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
        working_directory: Optional[str] = None,
        timeout: Optional[int] = 60,
        capture_output: bool = True,
        capture_errors: bool = True,
        bash_executable: Optional[str] = None
    ) -> Dict[str, Any]:
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

        # Resolve the shell executable (explicit override or auto-detected)
        shell_path = bash_executable or self._find_shell()
        if shell_path is None:
            self.report_error("Bash not found")
            return {
                "success": False,
                "error": (
                    "No Bash executable found. Install bash or ensure a POSIX "
                    "shell (sh) is on PATH."
                ),
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        try:
            # Determine working directory
            if working_directory:
                abs_working_dir = os.path.abspath(working_directory)
                if not os.path.exists(abs_working_dir):
                    return {
                        "success": False,
                        "error": f"Working directory does not exist: {abs_working_dir}",
                        "exit_code": -1,
                        "working_directory": working_directory
                    }
            else:
                abs_working_dir = os.getcwd()

            norm_working_dir = norm_path(abs_working_dir)

            # Report the code to be executed
            code_preview = code
            if len(code) > 200:
                code_preview = code[:200] + "..."
            self.report_start(f"Executing Bash code in {norm_working_dir}:\n{code_preview}")

            # Build shell command
            # Use -c for both single commands and multi-line scripts.
            # --noprofile/--norc skip startup files for faster, reproducible
            # execution; they are only valid for bash, not for POSIX sh.
            if self._is_bash(shell_path):
                shell_command = [shell_path, "--noprofile", "--norc", "-c", code]
            else:
                shell_command = [shell_path, "-c", code]

            # Execute with real-time streaming
            import threading
            import queue

            # Initialize captured output
            captured_stdout = []
            captured_stderr = []

            # Start the subprocess
            # BASH_ENV/ENV are cleared so non-interactive shells do not source
            # unexpected startup files, keeping execution reproducible.
            env = {**os.environ, "BASH_ENV": "", "ENV": ""}
            process = subprocess.Popen(
                shell_command,
                cwd=abs_working_dir,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True,
                shell=False,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                env=env
            )

            # Queue for handling output from threads
            output_queue = queue.Queue()

            def read_stream(stream, stream_name, capture_list):
                """Read from a stream and put lines into the queue."""
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            output_queue.put((stream_name, line.rstrip('\r\n')))
                            if capture_list is not None:
                                capture_list.append(line)
                    stream.close()
                except Exception as e:
                    output_queue.put(('error', f"Error reading {stream_name}: {e}"))

            # Start reader threads for stdout and stderr
            threads = []
            if capture_output and process.stdout:
                stdout_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stdout, 'stdout', captured_stdout),
                    daemon=True
                )
                stdout_thread.start()
                threads.append(stdout_thread)

            if capture_errors and process.stderr:
                stderr_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stderr, 'stderr', captured_stderr),
                    daemon=True
                )
                stderr_thread.start()
                threads.append(stderr_thread)

            # Monitor the process and display output in real-time
            exit_code = None
            start_display_time = time.time()
            displayed_any_output = False

            while True:
                # Check if process has finished
                exit_code = process.poll()
                process_finished = exit_code is not None

                # Process any available output
                try:
                    while True:
                        stream_name, line = output_queue.get_nowait()
                        if stream_name == 'stdout':
                            if not displayed_any_output:
                                print()  # Add newline after the initial message
                                displayed_any_output = True
                            print(line)
                        elif stream_name == 'stderr':
                            if not displayed_any_output:
                                print()  # Add newline after the initial message
                                displayed_any_output = True
                            print(line, file=sys.stderr)
                        elif stream_name == 'error':
                            print(f"STREAM ERROR: {line}", file=sys.stderr)
                except queue.Empty:
                    pass

                # If process finished, break
                if process_finished:
                    break

                # Handle timeout
                if timeout is not None:
                    elapsed = time.time() - start_display_time
                    if elapsed > timeout:
                        process.kill()
                        exit_code = -1
                        break

                # Small delay to prevent busy waiting
                time.sleep(0.01)

            # Wait for reader threads to finish
            for thread in threads:
                thread.join(timeout=1)

            # Ensure all remaining output is processed
            try:
                while True:
                    stream_name, line = output_queue.get_nowait()
                    if stream_name == 'stdout':
                        if not displayed_any_output:
                            print()
                            displayed_any_output = True
                        print(line)
                    elif stream_name == 'stderr':
                        if not displayed_any_output:
                            print()
                            displayed_any_output = True
                        print(f"{line}", file=sys.stderr)
            except queue.Empty:
                pass

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Create result object similar to subprocess.CompletedProcess
            class MockResult:
                def __init__(self, returncode, stdout_lines, stderr_lines):
                    self.returncode = returncode
                    self.stdout = ''.join(stdout_lines) if stdout_lines else ""
                    self.stderr = ''.join(stderr_lines) if stderr_lines else ""

            result = MockResult(exit_code, captured_stdout, captured_stderr)

            # Determine success (exit code 0 typically means success)
            success = result.returncode == 0

            # Build result dictionary
            output_result = {
                "success": success,
                "exit_code": result.returncode,
                "command": code,
                "bash_executable": shell_path,
                "working_directory": working_directory or abs_working_dir,
                "execution_time_ms": execution_time_ms
            }

            if capture_output:
                output_result["stdout"] = result.stdout
            if capture_errors:
                output_result["stderr"] = result.stderr

            # Report result
            if success:
                output_summary = f"Completed in {execution_time_ms}ms"
                if capture_output and result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 0:
                        output_summary += f" ({len(lines)} lines output)"
                self.report_result(output_summary)
            else:
                error_msg = f"Exit code {result.returncode}"
                if capture_errors and result.stderr:
                    # Truncate long error messages for display
                    stderr_preview = result.stderr[:100].replace('\n', ' ')
                    if len(result.stderr) > 100:
                        stderr_preview += "..."
                    error_msg += f": {stderr_preview}"
                self.report_error(error_msg)
                output_result["error"] = f"Bash execution failed with exit code {result.returncode}"

            return output_result

        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Timeout after {timeout}s")
            return {
                "success": False,
                "error": f"Bash execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
            }

        except FileNotFoundError:
            self.report_error("Bash not found")
            return {
                "success": False,
                "error": (
                    f"Shell executable not found: {shell_path}. "
                    "Install bash or ensure a POSIX shell (sh) is available."
                ),
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to execute Bash: {str(e)}",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
            }


# CLI interface for testing
def main():
    """Command line interface for testing the RunBashCode tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute Bash code for AI function calling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c "ls -la | head -5"
  %(prog)s -c "for i in 1 2 3; do echo $i; done" -d "/tmp"
  %(prog)s -c "echo 'Hello World'" --json
  %(prog)s -f script.sh
        """
    )

    parser.add_argument("-c", "--code", help="Bash code to execute")
    parser.add_argument("-f", "--file", help="File containing Bash code")
    parser.add_argument("-d", "--directory", help="Working directory for execution")
    parser.add_argument("-s", "--shell", help="Shell executable to use (default: auto-detected bash, falling back to sh)")
    parser.add_argument("-t", "--timeout", type=int, default=60,
                       help="Timeout in seconds (default: 60)")
    parser.add_argument("--no-capture-output", action="store_true",
                       help="Don't capture standard output")
    parser.add_argument("--no-capture-errors", action="store_true",
                       help="Don't capture standard error")
    parser.add_argument("--json", "-j", action="store_true",
                       help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show verbose output")

    args = parser.parse_args()

    # Validate arguments
    if not args.code and not args.file:
        parser.error("Either --code or --file must be specified")

    if args.code and args.file:
        parser.error("Cannot specify both --code and --file")

    # Get code from file if specified
    code = args.code
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            return 1
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return 1

    # Create tool instance and execute
    tool_instance = RunBashCode()
    result = tool_instance.run(
        code=code,
        working_directory=args.directory,
        timeout=args.timeout,
        capture_output=not args.no_capture_output,
        capture_errors=not args.no_capture_errors,
        bash_executable=args.shell
    )

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✓ Bash execution successful (exit code {result['exit_code']})")
            print(f"  Working directory: {norm_path(result['working_directory'])}")
            print(f"  Execution time: {result['execution_time_ms']}ms")

            if args.verbose:
                print(f"  Executable: {result.get('bash_executable', 'unknown')}")
                print(f"\nCommand:")
                print(f"  {result['command']}")

            if 'stdout' in result and result['stdout']:
                print(f"\nOutput:")
                print(result['stdout'])

            if 'stderr' in result and result['stderr']:
                print(f"\nStderr:")
                print(result['stderr'])
        else:
            print(f"✗ Bash execution failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Exit code: {result['exit_code']}")

            if args.verbose:
                print(f"\nCommand:")
                print(f"  {result['command']}")

            if 'stdout' in result and result['stdout']:
                print(f"\nOutput:")
                print(result['stdout'])

            if 'stderr' in result and result['stderr']:
                print(f"\nStderr:")
                print(result['stderr'])

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
