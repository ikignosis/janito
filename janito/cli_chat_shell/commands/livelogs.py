def handle_livelogs(console, args=None, state=None, **kwargs):
    """
    /livelogs [N] - Show the last N lines of the livereload server logs (default: 20)
    """
    lines = 20
    if args and len(args) > 0 and str(args[0]).isdigit():
        lines = int(args[0])
    stdout_path = state.get("livereload_stdout_path") if state else None
    stderr_path = state.get("livereload_stderr_path") if state else None
    if not stdout_path and not stderr_path:
        console.print(
            "[yellow][livereload] No livereload log files found for this session.[/yellow]"
        )
        return
    stdout_lines = []
    stderr_lines = []
    if stdout_path:
        try:
            with open(stdout_path, encoding="utf-8") as f:
                stdout_lines = f.readlines()[-lines:]
            if stdout_lines:
                console.print(
                    f"[yellow][livereload][stdout] Tail of {stdout_path}:\n"
                    + "".join(stdout_lines)
                )
        except Exception as e:
            console.print(f"[red][livereload][stdout] Error: {e}[/red]")
    if stderr_path:
        try:
            with open(stderr_path, encoding="utf-8") as f:
                stderr_lines = f.readlines()[-lines:]
            if stderr_lines:
                console.print(
                    f"[red][livereload][stderr] Tail of {stderr_path}:\n"
                    + "".join(stderr_lines)
                )
        except Exception as e:
            console.print(f"[red][livereload][stderr] Error: {e}[/red]")
    if (not stdout_path or not stdout_lines) and (not stderr_path or not stderr_lines):
        console.print("[livereload] No output or errors captured in logs.")
