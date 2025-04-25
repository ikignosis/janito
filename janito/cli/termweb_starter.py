import sys
import subprocess
import tempfile
import time
import http.client
import os
from rich.console import Console
from janito.agent.runtime_config import runtime_config
from janito.cli.runner._termweb_log_utils import print_termweb_logs


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
                import importlib.util

                spec = importlib.util.find_spec("janito.termweb.app")
                if spec and spec.origin:
                    app_py_path = spec.origin
                else:
                    app_py_path = None
            except Exception:
                app_py_path = None
        if not app_py_path or not os.path.isfile(app_py_path):
            console.print(
                "[red][termweb][/red] Could not find app.py for termweb (tried source and installed package). Aborting startup."
            )
            runtime_config.set("termweb_port", None)
            return None, False, None, None
        termweb_stdout = tempfile.NamedTemporaryFile(
            prefix="termweb_stdout_", delete=False, mode="w", encoding="utf-8"
        )
        termweb_stderr = tempfile.NamedTemporaryFile(
            prefix="termweb_stderr_", delete=False, mode="w", encoding="utf-8"
        )
        termweb_proc = subprocess.Popen(
            [
                sys.executable,
                app_py_path,
                "--port",
                str(selected_port),
            ],
            stdout=termweb_stdout,
            stderr=termweb_stderr,
        )
        if wait_for_termweb(selected_port, timeout=3.0):
            console.print(
                f"[green]TermWeb started... Available at http://localhost:{selected_port}[/green]"
            )
            return termweb_proc, True, termweb_stdout.name, termweb_stderr.name
        else:
            termweb_proc.terminate()
            termweb_proc.wait()
            console.print(
                f"[red][termweb][/red] Startup failed: Bottle app did not respond on port {selected_port} within 3 seconds."
            )
            print_termweb_logs(termweb_stdout.name, termweb_stderr.name, console)
            runtime_config.set("termweb_port", None)
            return None, False, termweb_stdout.name, termweb_stderr.name
