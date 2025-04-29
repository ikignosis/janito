import sys
import subprocess
import tempfile
import time
import http.client
import os
from rich.console import Console


def wait_for_livereload(port, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("localhost", port, timeout=0.5)
            conn.request("GET", "/")
            resp = conn.getresponse()
            if resp.status in (200, 404):
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def start_livereload(selected_port):
    console = Console()
    with console.status("[cyan]Starting live reload server...", spinner="dots"):
        app_py_path = os.path.join(
            os.path.dirname(__file__), "..", "livereload", "app.py"
        )
        app_py_path = os.path.abspath(app_py_path)
        if not os.path.isfile(app_py_path):
            console.print("[red]Could not find livereload app.py![/red]")
            return None, False, None, None
        livereload_stdout = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", encoding="utf-8"
        )
        livereload_stderr = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", encoding="utf-8"
        )
        livereload_proc = subprocess.Popen(
            [sys.executable, app_py_path, "--port", str(selected_port)],
            stdout=livereload_stdout,
            stderr=livereload_stderr,
        )
        if wait_for_livereload(selected_port, timeout=3.0):
            console.print(
                f"LiveReload started... Available at http://localhost:{selected_port}"
            )
            return livereload_proc, True, livereload_stdout.name, livereload_stderr.name
        else:
            livereload_proc.terminate()
            livereload_proc.wait()
            from janito.cli.runner._livereload_log_utils import print_livereload_logs

            console.print(
                f"[red]Failed to start LiveReload on port {selected_port}. Check logs for details.[/red]"
            )
            print_livereload_logs(livereload_stdout.name, livereload_stderr.name)
            return None, False, livereload_stdout.name, livereload_stderr.name
