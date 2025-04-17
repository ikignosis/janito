from janito.agent.tool_handler import ToolHandler
from janito.agent.runtime_config import runtime_config
from janito.agent.tools.rich_utils import print_info, print_success, print_error
import subprocess
import threading
import queue
from typing import Optional

import tempfile
import os
from janito.agent.tools.tool_base import ToolBase

def _run_bash_command(command: str, result_queue: 'queue.Queue', trust: bool = False):
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

# Converted run_bash_command free-function into RunBashCommandTool
class RunBashCommandTool(ToolBase):
    """Execute a non-interactive bash command and capture live output."""
    def call(self, command: str, timeout: int = 60, require_confirmation: bool = False) -> str:
        trust = runtime_config.get('trust', False)
        print_info(f"[run_bash_command] Running: {command}")
        if require_confirmation:
            print_error(f"⚠️ Confirmation required for: {command}\nType 'yes' to confirm:")
            resp = input("> ")
            if resp.strip().lower() != 'yes':
                print_error("❌ Command not confirmed by user.")
                return "❌ Command not confirmed by user."
        print_info(f"🐛 Running bash command: [bold]{command}[/bold] (timeout: {timeout}s)")
        result_queue = queue.Queue()
        thread = threading.Thread(target=_run_bash_command, args=(command, result_queue, trust))
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            # No direct way to kill a thread, so we just note timeout
            result = {'stdout_file': '', 'stderr_file': '', 'error': f'Thread timed out after {timeout} seconds.', 'returncode': -1}
        elif not result_queue.empty():
            result = result_queue.get()
        else:
            result = {'stdout_file': '', 'stderr_file': '', 'error': 'No result returned from thread.', 'returncode': -1}
        print_info("🐛 Bash command execution completed.")
        print_info(f"Return code: {result['returncode']}")
        if result.get('error'):
            print_error(f"Error: {result['error']}")
            return f"❌ Error: {result['error']}\nreturncode: {result['returncode']}"
        stdout_lines = stderr_lines = 0
        for key in ('stdout_file','stderr_file'):
            try:
                with open(result[key], 'r', encoding='utf-8') as f:
                    if key=='stdout_file': stdout_lines = sum(1 for _ in f)
                    else: stderr_lines = sum(1 for _ in f)
            except: pass
        print_success(f"✅ Success\nstdout: {result['stdout_file']} (lines: {stdout_lines})\nstderr: {result['stderr_file']} (lines: {stderr_lines})")
        return (
            f"✅ Bash command executed.\n"
            f"stdout saved to: {result['stdout_file']} (lines: {stdout_lines})\n"
            f"stderr saved to: {result['stderr_file']} (lines: {stderr_lines})\n"
            f"returncode: {result['returncode']}"
        )

ToolHandler.register_tool(RunBashCommandTool, name="run_bash_command")
