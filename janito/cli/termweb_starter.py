import sys
import subprocess
import tempfile
import time
import http.client
import os
from rich.console import Console
from janito.cli._termweb_log_utils import print_termweb_logs
from janito.i18n import tr


def wait_for_termweb(port, timeout=3.0):
    """Polls the Bottle app root endpoint until it responds or timeout (seconds) is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("localhost", port, timeout=0.5)
            conn.request("GET", "/")
            resp = conn.getresponse()
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def start_termweb(selected_port):
    """
    Start the termweb server on the given port, with rich spinner and logging.
    Returns (termweb_proc, started: bool)
    """
    console = Console()
    with console.status("[cyan]Starting web server...", spinner="dots"):
        # Step 1: Try source path
        app_py_path = os.path.join(os.path.dirname(__file__), "..", "termweb", "app.py")
        app_py_path = os.path.abspath(app_py_path)
        if not os.path.isfile(app_py_path):
            # Step 2: Try installed package
            try:
                import janito_termweb

                app_py_path = janito_termweb.__file__.replace("__init__.py", "app.py")
            except ImportError:
                console.print("[red]Could not find termweb app.py![/red]")
                return None, False, None, None
        termweb_stdout = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", encoding="utf-8"
        )
        termweb_stderr = tempfile.NamedTemporaryFile(
            delete=False, mode="w+", encoding="utf-8"
        )
        termweb_proc = subprocess.Popen(
            [sys.executable, app_py_path, "--port", str(selected_port)],
            stdout=termweb_stdout,
            stderr=termweb_stderr,
        )
        if wait_for_termweb(selected_port, timeout=3.0):
            console.print(
                tr(
                    "TermWeb started... Available at http://localhost:{selected_port}",
                    selected_port=selected_port,
                )
            )
            return termweb_proc, True, termweb_stdout.name, termweb_stderr.name
        else:
            termweb_proc.terminate()
            termweb_proc.wait()
            console.print(
                f"[red]Failed to start TermWeb on port {selected_port}. Check logs for details.[/red]"
            )
            print_termweb_logs(termweb_stdout.name, termweb_stderr.name, console)
            return None, False, termweb_stdout.name, termweb_stderr.name
