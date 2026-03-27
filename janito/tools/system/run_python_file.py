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

import subprocess
import json
import os
import sys
import threading
import queue
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool, norm_path
from ..decorator import tool


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
        working_directory: Optional[str] = None,
        timeout: Optional[int] = 60,
        capture_output: bool = True,
        capture_errors: bool = True,
        python_executable: Optional[str] = None,
        additional_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
            # Validate file path
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"Python file does not exist: {file_path}",
                    "exit_code": -1,
                    "file_path": file_path
                }
            
            abs_file_path = os.path.abspath(file_path)
            norm_file_path = norm_path(abs_file_path)
            
            # Determine working directory
            if working_directory:
                abs_working_dir = os.path.abspath(working_directory)
                if not os.path.exists(abs_working_dir):
                    return {
                        "success": False,
                        "error": f"Working directory does not exist: {abs_working_dir}",
                        "exit_code": -1,
                        "file_path": file_path,
                        "working_directory": working_directory
                    }
            else:
                # Use the directory containing the Python file as working directory by default
                abs_working_dir = os.path.dirname(abs_file_path)
            
            norm_working_dir = norm_path(abs_working_dir)
            
            # Determine Python executable
            if python_executable is None:
                python_executable = sys.executable
            
            # Build command preview for display
            cmd_parts = [python_executable, norm_file_path]
            if additional_args:
                cmd_parts.extend(additional_args)
            command_preview = " ".join(cmd_parts)
            if len(command_preview) > 200:
                command_preview = command_preview[:200] + "..."
            
            # Report the file to be executed
            self.report_start(f"Executing Python file in {norm_working_dir}:\n{command_preview}")
            
            # Build Python command
            python_command = [python_executable, abs_file_path]
            if additional_args:
                python_command.extend(additional_args)
            
            # Initialize captured output
            captured_stdout = []
            captured_stderr = []
            
            # Start the subprocess
            process = subprocess.Popen(
                python_command,
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
                                displayed_any_output = True
                            print(line)
                        elif stream_name == 'stderr':
                            if not displayed_any_output:
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
                            displayed_any_output = True
                        print(line)
                    elif stream_name == 'stderr':
                        if not displayed_any_output:
                            displayed_any_output = True
                        print(line, file=sys.stderr)
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
                "command": " ".join(python_command),
                "file_path": file_path,
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
                output_result["error"] = f"Python file execution failed with exit code {result.returncode}"
            
            return output_result
            
        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Timeout after {timeout}s")
            return {
                "success": False,
                "error": f"Python file execution timed out after {timeout} seconds",
                "exit_code": -1,
                "command": " ".join(python_command) if 'python_command' in locals() else "",
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
            }
            
        except FileNotFoundError:
            self.report_error("Python executable not found")
            return {
                "success": False,
                "error": f"Python executable not found: {python_executable}",
                "exit_code": -1,
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_error(f"Execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to execute Python file: {str(e)}",
                "exit_code": -1,
                "file_path": file_path,
                "working_directory": working_directory or os.getcwd(),
                "execution_time_ms": execution_time_ms
            }


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
        """
    )
    
    parser.add_argument("file", help="Python file to execute")
    parser.add_argument("-d", "--directory", help="Working directory for execution")
    parser.add_argument("-p", "--python", help="Python executable to use (default: current interpreter)")
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
    parser.add_argument("--", dest="additional_args", nargs=argparse.REMAINDER,
                       help="Additional arguments to pass to the Python script")
    
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
        additional_args=args.additional_args
    )
    
    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"? Python file execution successful (exit code {result['exit_code']})")
            print(f"  File: {norm_path(result['file_path'])}")
            print(f"  Working directory: {norm_path(result['working_directory'])}")
            print(f"  Execution time: {result['execution_time_ms']}ms")
            
            if args.verbose:
                print(f"\nCommand:")
                print(f"  {result['command']}")
            
            if 'stdout' in result and result['stdout']:
                print(f"\nOutput:")
                print(result['stdout'])
            
            if 'stderr' in result and result['stderr']:
                print(f"\nStderr:")
                print(result['stderr'])
        else:
            print(f"? Python file execution failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Exit code: {result['exit_code']}")
            print(f"  File: {norm_path(result['file_path'])}")
            
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
