import sys
import subprocess
import tempfile
import time
import http.client
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
        termweb_stdout = tempfile.NamedTemporaryFile(
            prefix="termweb_stdout_", delete=False, mode="w", encoding="utf-8"
        )
        termweb_stderr = tempfile.NamedTemporaryFile(
            prefix="termweb_stderr_", delete=False, mode="w", encoding="utf-8"
        )
        termweb_proc = subprocess.Popen(
            [
                sys.executable,
                "janito/termweb/app.py",
                "--port",
                str(selected_port),
            ],
            stdout=termweb_stdout,
            stderr=termweb_stderr,
        )
        if wait_for_termweb(selected_port, timeout=3.0):
            console.print(
                f"[green]Started and available at http://localhost:{selected_port}[/green]"
            )
            return termweb_proc, True
        else:
            termweb_proc.terminate()
            termweb_proc.wait()
            console.print(
                f"[red][termweb][/red] Startup failed: Bottle app did not respond on port {selected_port} within 3 seconds."
            )
            print_termweb_logs(termweb_stdout.name, termweb_stderr.name, console)
            runtime_config.set("termweb_port", None)
            return None, False
