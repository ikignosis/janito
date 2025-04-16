from janito.agent.tool_handler import ToolHandler
from janito.agent.runtime_config import runtime_config
from janito.agent.tools.rich_utils import print_info, print_success, print_error
import subprocess
import multiprocessing
from typing import Optional

import tempfile
import os

def _run_bash_command(command: str, result_queue: 'multiprocessing.Queue', trust: bool = False):
    import subprocess
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8', suffix='.stdout') as stdout_file, \
         tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8', suffix='.stderr') as stderr_file:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace'
        )
        while True:
            stdout_line = process.stdout.readline() if process.stdout else ''
            stderr_line = process.stderr.readline() if process.stderr else ''
            if stdout_line:
                if not trust:
                    print(stdout_line, end='')
                stdout_file.write(stdout_line)
                stdout_file.flush()
            if stderr_line:
                if not trust:
                    print(stderr_line, end='')
                stderr_file.write(stderr_line)
                stderr_file.flush()
            if not stdout_line and not stderr_line and process.poll() is not None:
                break
        # Capture any remaining output after process ends
        if process.stdout:
            for line in process.stdout:
                if not trust:
                    print(line, end='')
                stdout_file.write(line)
        if process.stderr:
            for line in process.stderr:
                if not trust:
                    print(line, end='')
                stderr_file.write(line)
        stdout_file_path = stdout_file.name
        stderr_file_path = stderr_file.name
    result_queue.put({
        'stdout_file': stdout_file_path,
        'stderr_file': stderr_file_path,
        'returncode': process.returncode
    })


@ToolHandler.register_tool
def run_bash_command(command: str, timeout: int = 60, require_confirmation: bool = False) -> str:
    trust = runtime_config.get('trust', False)
    """
    Execute a non-interactive bash command and print output live.

    If require_confirmation is True, the user will be prompted to confirm execution before running the command.

    Args:
        command (str): The Bash command to execute.
        timeout (int): Maximum number of seconds to allow the command to run. Default is 60.

    Returns:
        str: A formatted message string containing stdout, stderr, and return code.
    """
    print_info(f"[run_bash_command] Running: {command}")
    if require_confirmation:
        # Prompt the user for confirmation directly
        resp = input(f"Are you sure you want to run this command?\n\n{command}\n\nType 'yes' to confirm: ")
        if resp.strip().lower() != 'yes':
            print_error("❌ Command not confirmed by user.")
            return "❌ Command not confirmed by user."
    print_info(f"🐛 Running bash command: [bold]{command}[/bold] (timeout: {timeout}s)")
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_run_bash_command, args=(command, result_queue, trust))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        result = {'stdout_file': '', 'stderr_file': '', 'error': f'Process timed out after {timeout} seconds.', 'returncode': -1}
    elif not result_queue.empty():
        result = result_queue.get()
    else:
        result = {'stdout_file': '', 'stderr_file': '', 'error': 'No result returned from process.', 'returncode': -1}
    if trust:
        stdout_lines = 0
        stderr_lines = 0
        try:
            with open(result['stdout_file'], 'r', encoding='utf-8') as f:
                stdout_lines = sum(1 for _ in f)
        except Exception:
            pass
        try:
            with open(result['stderr_file'], 'r', encoding='utf-8') as f:
                stderr_lines = sum(1 for _ in f)
        except Exception:
            pass
        print_success(f"✅ Success (trust mode)\nstdout: {result['stdout_file']} (lines: {stdout_lines})\nstderr: {result['stderr_file']} (lines: {stderr_lines})")
        return (
            f"✅ Bash command executed in trust mode. Output is stored at:\n"
            f"stdout: {result['stdout_file']} (lines: {stdout_lines})\n"
            f"stderr: {result['stderr_file']} (lines: {stderr_lines})\n"
            f"returncode: {result['returncode']}\n"
            "To examine the output, use the file-related tools such as get_lines or search_files on the above files."
        )
    print_info("🐛 Bash command execution completed.")
    print_info(f"Return code: {result['returncode']}")
    if result.get('error'):
        print_error(f"Error: {result['error']}")
        return f"❌ Error: {result['error']}\nreturncode: {result['returncode']}"
    stdout_lines = 0
    stderr_lines = 0
    try:
        with open(result['stdout_file'], 'r', encoding='utf-8') as f:
            stdout_lines = sum(1 for _ in f)
    except Exception:
        pass
    try:
        with open(result['stderr_file'], 'r', encoding='utf-8') as f:
            stderr_lines = sum(1 for _ in f)
    except Exception:
        pass
    print_success(f"✅ Success\nstdout saved to: {result['stdout_file']} (lines: {stdout_lines})\nstderr saved to: {result['stderr_file']} (lines: {stderr_lines})")
    return (
        f"✅ Bash command executed.\n"
        f"stdout saved to: {result['stdout_file']} (lines: {stdout_lines})\n"
        f"stderr saved to: {result['stderr_file']} (lines: {stderr_lines})\n"
        f"returncode: {result['returncode']}\n"
        "\nTo examine the output, use the file-related tools such as get_lines or search_files on the above files."
    )

