def handle_help(console, **kwargs):
    console.print(
        """
[bold green]Available commands:[/bold green]
  /exit, exit     - Exit chat mode
  /restart  - Start a new conversation
  /help     - Show this help message
  /continue - Restore last saved conversation
  /prompt   - Show the system prompt
  /role     - Change the system role
  /clear    - Clear the terminal screen
  /multi    - Provide multiline input as next message
  /config   - Show or set configuration (see: /config show, /config set local|global key=value)
  /termweb-logs - Show the last lines of the latest termweb logs
  /livelogs  - Show live updates from the server log file (default: server.log)
  /termweb-status - Show status information about the running termweb server
  /verbose [on|off] - Show or set verbose mode for this session
"""
    )


def handle_clear(console, **kwargs):
    import os

    os.system("cls" if os.name == "nt" else "clear")


def handle_multi(console, shell_state=None, **kwargs):
    console.print(
        "[bold yellow]Multiline mode activated. Provide or write your text and press Esc + Enter to submit.[/bold yellow]"
    )
    if shell_state:
        shell_state.paste_mode = True
