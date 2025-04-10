from aurora.agent.tool_handler import ToolHandler
from aurora.agent.tools.rich_utils import print_info, print_bash_stdout, print_bash_stderr
import subprocess
import threading
from typing import Callable, Optional


@ToolHandler.register_tool
def bash_exec(command: str, on_progress: Optional[Callable[[dict], None]] = None) -> str:
    """
    command: The Bash command to execute.
    on_progress: Optional callback function for streaming progress updates.

    Execute a non interactive bash command and print output live.

    Returns:
    str: A formatted message string containing stdout, stderr, and return code.
    """
    print_info(f"[bash_exec] Executing command: {command}")
    result = {'stdout': '', 'stderr': '', 'returncode': None}

    def run_command():
        try:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace'
            )
            stdout_lines = []
            stderr_lines = []

            def read_stream(stream, collector, print_func, stream_name):
                for line in iter(stream.readline, ''):
                    collector.append(line)
                    print_func(line.rstrip())
                    if on_progress:
                        on_progress({'stream': stream_name, 'line': line.rstrip()})
                stream.close()

            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines, print_bash_stdout, 'stdout'))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines, print_bash_stderr, 'stderr'))
            stdout_thread.start()
            stderr_thread.start()
            stdout_thread.join()
            stderr_thread.join()
            result['returncode'] = process.wait()
            result['stdout'] = ''.join(stdout_lines)
            result['stderr'] = ''.join(stderr_lines)
        except Exception as e:
            result['stderr'] = str(e)
            result['returncode'] = -1

    thread = threading.Thread(target=run_command)
    thread.start()
    thread.join()  # Wait for the thread to finish

    print_info(f"[bash_exec] Command execution completed.")
    print_info(f"[bash_exec] Return code: {result['returncode']}")

    return f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}\nreturncode: {result['returncode']}"
