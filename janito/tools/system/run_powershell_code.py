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

import subprocess
import json
import os
import shutil
import sys
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool, norm_path
from ..decorator import tool


# Candidate executable names, in order of preference.
# 'pwsh' is PowerShell Core 6+/7+ (modern, cross-platform) and is preferred;
# 'powershell' is Windows PowerShell 5.1 (built into Windows, legacy).
_POWERSHELL_CANDIDATES = ("pwsh", "pwsh.exe", "powershell", "powershell.exe")


def _well_known_powershell_paths() -> List[str]:
    """
    Build a list of well-known PowerShell Core install locations.

    These are probed as a fallback when no PowerShell executable is found
    on PATH. Only existing paths are relevant; non-existent ones are skipped.
    """
    paths = []

    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        paths.extend([
            os.path.join(program_files, "PowerShell", "7", "pwsh.exe"),
            os.path.join(program_files_x86, "PowerShell", "7", "pwsh.exe"),
        ])
        if local_app_data:
            paths.append(
                os.path.join(local_app_data, "Programs", "PowerShell", "7", "pwsh.exe")
            )
    elif sys.platform == "darwin":
        paths.extend([
            "/usr/local/bin/pwsh",                 # Homebrew (Intel) / pkg installer symlink
            "/opt/homebrew/bin/pwsh",              # Homebrew (Apple Silicon)
            "/usr/local/microsoft/powershell/7/pwsh",  # pkg installer payload
        ])
    else:  # Linux and other POSIX
        paths.extend([
            "/usr/bin/pwsh",
            "/usr/local/bin/pwsh",
            "/opt/microsoft/powershell/7/pwsh",
            "/snap/bin/pwsh",
        ])

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
    _powershell_path: Optional[str] = None
    _powershell_checked: bool = False

    @classmethod
    def _find_powershell(cls) -> Optional[str]:
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
        working_directory: Optional[str] = None,
        timeout: Optional[int] = 60,
        capture_output: bool = True,
        capture_errors: bool = True
    ) -> Dict[str, Any]:
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

        # Resolve the PowerShell executable (prefers PowerShell Core 'pwsh')
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
            self.report_start(f"Executing PowerShell code in {norm_working_dir}:\n{code_preview}")

            # Wrapped in try/catch: setting console encodings can fail when
            # stdin/stdout are redirected (common with pwsh on non-Windows),
            # and must never abort the user's script.
            encoding_prefix = (
                "try { $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}; "
                "try { $InputEncoding = [Console]::InputEncoding = [System.Text.Encoding]::UTF8 } catch {}; "
            )
            code_with_encoding = encoding_prefix + code

            # Build PowerShell command
            # Use -Command for both single commands and multi-line scripts.
            # -NoProfile for faster execution, -NonInteractive to never block
            # on prompts. -ExecutionPolicy only exists on Windows.
            ps_command = [powershell_path, "-NoProfile", "-NonInteractive"]
            if os.name == "nt":
                ps_command += ["-ExecutionPolicy", "Bypass"]
            ps_command += ["-Command", code_with_encoding]
            
            # Execute PowerShell with real-time streaming
            import threading
            import queue
            
            # Initialize captured output
            captured_stdout = []
            captured_stderr = []
            
            # Start the subprocess
            process = subprocess.Popen(
                ps_command,
                cwd=abs_working_dir,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True,
                shell=False,
                bufsize=1,  # Line buffered
                universal_newlines=True
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
                "powershell_executable": powershell_path,
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
                output_result["error"] = f"PowerShell execution failed with exit code {result.returncode}"
            
            return output_result
            
        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Timeout after {timeout}s")
            return {
                "success": False,
                "error": f"PowerShell execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
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
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to execute PowerShell: {str(e)}",
                "exit_code": -1,
                "command": code,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
            }


# CLI interface for testing
def main():
    """Command line interface for testing the RunPowerShellCode tool."""
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
        """
    )
    
    parser.add_argument("-c", "--code", help="PowerShell code to execute")
    parser.add_argument("-f", "--file", help="File containing PowerShell code")
    parser.add_argument("-d", "--directory", help="Working directory for execution")
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
    tool_instance = RunPowerShellCode()
    result = tool_instance.run(
        code=code,
        working_directory=args.directory,
        timeout=args.timeout,
        capture_output=not args.no_capture_output,
        capture_errors=not args.no_capture_errors
    )
    
    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✓ PowerShell execution successful (exit code {result['exit_code']})")
            print(f"  Working directory: {norm_path(result['working_directory'])}")
            print(f"  Execution time: {result['execution_time_ms']}ms")

            if args.verbose:
                print(f"  Executable: {result.get('powershell_executable', 'unknown')}")
                print(f"\nCommand:")
                print(f"  {result['command']}")
            
            if 'stdout' in result and result['stdout']:
                print(f"\nOutput:")
                print(result['stdout'])
            
            if 'stderr' in result and result['stderr']:
                print(f"\nStderr:")
                print(result['stderr'])
        else:
            print(f"✗ PowerShell execution failed")
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
