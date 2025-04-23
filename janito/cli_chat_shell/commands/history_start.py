from prompt_toolkit.history import InMemoryHistory
import os


def handle_start(console, state, **kwargs):
    save_path = os.path.join(".janito", "last_conversation.json")

    # Clear in-memory conversation and prompt history
    state["messages"].clear()
    state["history_list"].clear()
    state["mem_history"] = InMemoryHistory()
    state["last_usage_info"] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
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
        pass

    console.print(
        "[bold green]Conversation history has been started (context reset).[/bold green]"
    )
