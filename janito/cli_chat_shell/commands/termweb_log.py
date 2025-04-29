import http.client
from rich.console import Console
from janito.agent.runtime_config import runtime_config


def is_termweb_running(port):
    """Check if termweb is running by making an HTTP request to the root endpoint."""
    try:
        conn = http.client.HTTPConnection("localhost", port, timeout=0.5)
        conn.request("GET", "/")
        resp = conn.getresponse()
        return resp.status == 200
    except Exception:
        return False


def handle_termweb_log_tail(console: Console, *args, shell_state=None, **kwargs):
    lines = 20
    if args and args[0].isdigit():
        lines = int(args[0])
    stdout_path = shell_state.termweb_stdout_path if shell_state else None
    stderr_path = shell_state.termweb_stderr_path if shell_state else None
    if not stdout_path and not stderr_path:
        console.print(
            "[yellow][termweb] No termweb log files found for this session.[/yellow]"
        )
        return
    if stdout_path:
        try:
            with open(stdout_path, encoding="utf-8") as f:
                stdout_lines = f.readlines()[-lines:]
            if stdout_lines:
                console.print(
                    f"[yellow][termweb][stdout] Tail of {stdout_path}:\n"
                    + "".join(stdout_lines)
                )
        except Exception:
            pass
    if stderr_path:
        try:
            with open(stderr_path, encoding="utf-8") as f:
                stderr_lines = f.readlines()[-lines:]
            if stderr_lines:
                console.print(
                    f"[red][termweb][stderr] Tail of {stderr_path}:\n"
                    + "".join(stderr_lines)
                )
        except Exception:
            pass
    if (not stdout_path or not stdout_lines) and (not stderr_path or not stderr_lines):
        console.print("[termweb] No output or errors captured in logs.")


def handle_termweb_status(console: Console, *args, shell_state=None, **kwargs):
    if shell_state is None:
        console.print(
            "[red]No shell state available. Cannot determine termweb status.[/red]"
        )
        return
    port = getattr(shell_state, "termweb_port", None)
    port_source = "shell_state"
    if not port:
        port = runtime_config.get("termweb_port")
        port_source = "runtime_config"
    pid = getattr(shell_state, "termweb_pid", None)
    stdout_path = getattr(shell_state, "termweb_stdout_path", None)
    stderr_path = getattr(shell_state, "termweb_stderr_path", None)
    running = False
    if port:
        running = is_termweb_running(port)
    console.print("[bold cyan]TermWeb Server Status:[/bold cyan]")
    console.print(f"  Running: {'[green]Yes[/green]' if running else '[red]No[/red]'}")
    if pid:
        console.print(f"  PID: {pid}")
    if port:
        console.print(f"  Port: {port} (from {port_source})")
        url = f"http://localhost:{port}/"
        console.print(f"  URL: [underline blue]{url}[/underline blue]")
    else:
        console.print(
            "  [yellow]No port configured in state or runtime_config.[/yellow]"
        )
    if stdout_path:
        console.print(f"  Stdout log: {stdout_path}")
    if stderr_path:
        console.print(f"  Stderr log: {stderr_path}")
