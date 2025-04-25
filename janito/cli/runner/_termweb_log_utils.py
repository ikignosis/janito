def print_termweb_logs(stdout_path, stderr_path, console):
    try:
        with open(stdout_path, encoding="utf-8") as f:
            stdout_content = f.read().strip()
    except Exception:
        stdout_content = None
    try:
        with open(stderr_path, encoding="utf-8") as f:
            stderr_content = f.read().strip()
    except Exception:
        stderr_content = None
    if stdout_content:
        console.print("[yellow][termweb][stdout] Output:\n" + stdout_content)
    if stderr_content:
        console.print("[red][termweb][stderr] Errors:\n" + stderr_content)
    if not stdout_content and not stderr_content:
        console.print("[termweb] No output or errors captured in logs.")
