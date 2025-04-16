from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_bash_stdout, print_bash_stderr
import subprocess
import multiprocessing
from typing import Callable, Optional


import tempfile
import os

def _run_bash_command(command: str, result_queue: 'multiprocessing.Queue'):
    import subprocess
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8', suffix='.stdout') as stdout_file, \
             tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8', suffix='.stderr') as stderr_file:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace'
            )
            while True:
                stdout_line = process.stdout.readline() if process.stdout else ''
                stderr_line = process.stderr.readline() if process.stderr else ''
                if stdout_line:
                    print(stdout_line, end='')
                    stdout_file.write(stdout_line)
                    stdout_file.flush()
                if stderr_line:
                    print(stderr_line, end='')
                    stderr_file.write(stderr_line)
                    stderr_file.flush()
                if not stdout_line and not stderr_line and process.poll() is not None:
                    break
            # Capture any remaining output after process ends
            if process.stdout:
                for line in process.stdout:
                    print(line, end='')
                    stdout_file.write(line)
            if process.stderr:
                for line in process.stderr:
                    print(line, end='')
                    stderr_file.write(line)
            stdout_file_path = stdout_file.name
            stderr_file_path = stderr_file.name
        result_queue.put({
            'stdout_file': stdout_file_path,
            'stderr_file': stderr_file_path,
            'returncode': process.returncode
        })
    except Exception as e:
        result_queue.put({
            'stdout_file': '',
            'stderr_file': '',
            'error': str(e),
            'returncode': -1
        })

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
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_run_bash_command, args=(command, result_queue))
    process.start()
    process.join()
    if not result_queue.empty():
        result = result_queue.get()
    else:
        result = {'stdout_file': '', 'stderr_file': '', 'error': 'No result returned from process.', 'returncode': -1}
    print_info(f"[bash_exec] Command execution completed.")
    print_info(f"[bash_exec] Return code: {result['returncode']}")
    if result.get('error'):
        return f"Error: {result['error']}\nreturncode: {result['returncode']}"
    return (
        f"stdout saved to: {result['stdout_file']}\n"
        f"stderr saved to: {result['stderr_file']}\n"
        f"returncode: {result['returncode']}\n"
        "\nTo examine the output, use the file-related tools such as view_file or grep_search on the above files."
    )
