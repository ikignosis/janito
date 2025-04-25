import os
from rich.console import Console


def handle_termweb_log_tail(console: Console, *args, state=None, **kwargs):
    """Show the last N lines of the current session's termweb logs (stdout and stderr)."""
    lines = 20
    if args and args[0].isdigit():
        lines = int(args[0])
    if state is None:
        console.print(
            "[red]No shell state available. Cannot locate termweb logs.[/red]"
        )
        return
    stdout_path = state.get("termweb_stdout_path")
    stderr_path = state.get("termweb_stderr_path")
    if not stdout_path and not stderr_path:
        console.print(
            "[yellow][termweb] No termweb log files found for this session.[/yellow]"
        )
        return
    if stdout_path and os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as f:
            stdout_lines = f.readlines()[-lines:]
        if stdout_lines:
            console.print(
                f"[yellow][termweb][stdout] Tail of {stdout_path}:\n"
                + "".join(stdout_lines)
            )
    if stderr_path and os.path.exists(stderr_path):
        with open(stderr_path, encoding="utf-8") as f:
            stderr_lines = f.readlines()[-lines:]
        if stderr_lines:
            console.print(
                f"[red][termweb][stderr] Tail of {stderr_path}:\n"
                + "".join(stderr_lines)
            )
    if (not stdout_path or not os.path.exists(stdout_path) or not stdout_lines) and (
        not stderr_path or not os.path.exists(stderr_path) or not stderr_lines
    ):
        console.print("[termweb] No output or errors captured in logs.")


def handle_termweb_status(console: Console, *args, state=None, **kwargs):
    """Show status information about the running termweb server."""
    if state is None:
        console.print(
            "[red]No shell state available. Cannot determine termweb status.[/red]"
        )
        return
    pid = state.get("termweb_pid")
    port = state.get("termweb_port")
    stdout_path = state.get("termweb_stdout_path")
    stderr_path = state.get("termweb_stderr_path")
    running = False
    if pid:
        try:
            os.kill(pid, 0)
            running = True
        except Exception:
            running = False
    console.print("[bold cyan]TermWeb Server Status:[/bold cyan]")
    console.print(f"  Running: {'[green]Yes[/green]' if running else '[red]No[/red]'}")
    if pid:
        console.print(f"  PID: {pid}")
    if port:
        console.print(f"  Port: {port}")
        url = f"http://localhost:{port}/"
        console.print(f"  URL: [underline blue]{url}[/underline blue]")
    if stdout_path:
        console.print(f"  Stdout log: {stdout_path}")
    if stderr_path:
        console.print(f"  Stderr log: {stderr_path}")
