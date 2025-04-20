from prompt_toolkit.history import InMemoryHistory
import os
import json


def handle_continue(console, state, **kwargs):
    save_path = os.path.join(".janito", "last_conversation.json")
    if not os.path.exists(save_path):
        console.print("[bold red]No saved conversation found.[/bold red]")
        return

    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    state["messages"].clear()
    state["messages"].extend(data.get("messages", []))
    state["history_list"].clear()
    state["history_list"].extend(data.get("prompts", []))
    state["mem_history"] = InMemoryHistory()
    for item in state["history_list"]:
        state["mem_history"].append_string(item)
    state["last_usage_info"] = data.get("last_usage_info")
    console.print("[bold green]Conversation restored from last session.[/bold green]")


def handle_history(console, state, *args, **kwargs):
    messages = state.get("messages", [])
    if not args:
        # Default: last 5 messages
        start = max(0, len(messages) - 5)
        end = len(messages)
    elif len(args) == 1:
        count = int(args[0])
        start = max(0, len(messages) - count)
        end = len(messages)
    elif len(args) >= 2:
        start = int(args[0])
        end = int(args[1]) + 1  # inclusive
    else:
        start = 0
        end = len(messages)

    console.print(
        f"[bold cyan]Showing messages {start} to {end - 1} (total {len(messages)}):[/bold cyan]"
    )
    for idx, msg in enumerate(messages[start:end], start=start):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        console.print(f"[bold]{idx} [{role}]:[/bold] {content}")
