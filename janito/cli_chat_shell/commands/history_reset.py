from prompt_toolkit.history import InMemoryHistory
import os


def handle_reset(console, state, **kwargs):
    save_path = os.path.join(".janito", "last_conversation.json")

    # Clear in-memory conversation and prompt history
    state["messages"].clear()
    state["history_list"].clear()
    state["mem_history"] = InMemoryHistory()
    state["last_usage_info"] = None
    state["last_elapsed"] = None

    # Delete saved conversation file if exists
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
            console.print(
                "[bold yellow]Deleted saved conversation history.[/bold yellow]"
            )
        except Exception as e:
            console.print(
                f"[bold red]Failed to delete saved conversation:[/bold red] {e}"
            )
    else:
        console.print("[bold yellow]No saved conversation to delete.[/bold yellow]")

    console.print("[bold green]Conversation history has been reset.[/bold green]")
