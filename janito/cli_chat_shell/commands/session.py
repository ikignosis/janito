def handle_history(console, shell_state=None, *args, **kwargs):
    if shell_state and hasattr(shell_state, "mem_history"):
        input_history = list(shell_state.mem_history.get_strings())
    else:
        input_history = []
    if not args:
        # Default: last 5 inputs
        start = max(0, len(input_history) - 5)
        end = len(input_history)
    elif len(args) == 1:
        count = int(args[0])
        start = max(0, len(input_history) - count)
        end = len(input_history)
    elif len(args) >= 2:
        start = int(args[0])
        end = int(args[1]) + 1  # inclusive
    else:
        start = 0
        end = len(input_history)

    console.print(
        f"[bold cyan]Showing input history {start} to {end - 1} (total {len(input_history)}):[/bold cyan]"
    )
    for idx, line in enumerate(input_history[start:end], start=start):
        console.print(f"{idx}: {line}")
        if isinstance(line, dict):
            role = line.get("role", "unknown")
            content = line.get("content", "")
        else:
            role = "user"
            content = line
        console.print(f"[bold]{idx} [{role}]:[/bold] {content}")
