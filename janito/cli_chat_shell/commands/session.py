from prompt_toolkit.history import InMemoryHistory
import os
import json


def handle_continue(console, shell_state=None, **kwargs):
    save_path = os.path.join(".janito", "last_conversation.json")
    if not os.path.exists(save_path):
        console.print("[bold red]No saved conversation found.[/bold red]")
        return

    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if shell_state and hasattr(shell_state, "history"):
        shell_state.history.clear()
    if shell_state:
        shell_state.mem_history = InMemoryHistory()
        for item in data.get("prompts", []):
            shell_state.mem_history.append_string(item)
        shell_state.last_usage_info = data.get("last_usage_info")
    console.print("[bold green]Conversation restored from last session.[/bold green]")


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
