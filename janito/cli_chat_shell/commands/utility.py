def handle_help(console, **kwargs):
    console.print(
        """
[bold green]Available commands:[/bold green]
  /exit, exit     - Exit chat mode
  /restart  - Restart the CLI
  /help     - Show this help message
  /continue - Restore last saved conversation
  /start    - Reset conversation history
  /prompt   - Show the system prompt
  /role     - Change the system role
  /clear    - Clear the terminal screen
  /multi    - Provide multiline input as next message
  /config   - Show or set configuration (see: /config show, /config set local|global key=value)
"""
    )


def handle_clear(console, **kwargs):
    import os

    os.system("cls" if os.name == "nt" else "clear")


def handle_multi(console, state, **kwargs):
    console.print(
        "[bold yellow]Multiline mode activated. Provide or write your text and press Esc + Enter to submit.[/bold yellow]"
    )
    state["paste_mode"] = True
