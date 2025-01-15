from typing import List, Optional
import readline
from rich.console import Console
from rich.table import Table

def display_history(limit: int = 20):
    """Display the command history with the specified limit.

    Args:
        limit: Maximum number of history entries to show
    """
    table = Table(title="Command History")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Command", style="white")

    # Get history items (most recent first)
    history_length = readline.get_current_history_length()
    start = max(1, history_length - limit + 1)

    for i in range(start, history_length + 1):
        cmd = readline.get_history_item(i)
        if cmd:
            table.add_row(str(i), cmd)

    console.print(table)
from rich.prompt import Prompt

console = Console()
import atexit
from pathlib import Path
from janito.config import config


def setup_history():
    """Setup readline history file persistence."""
    history_dir = config.workspace_dir / '.janito'
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / 'command_history'

    # Enable history file persistence
    readline.set_history_length(1000)

    # Read existing history
    if history_file.exists():
        readline.read_history_file(str(history_file))

    return history_file


def prompt_user(message: str, choices: List[str] = None, show_help: bool = True) -> str:
    """Display a simple user prompt with readline support and optional choices.

    Supports various keyboard shortcuts for navigation and editing.
    Use show_shortcuts() to see all available shortcuts.

    Args:
        message: The prompt message to display
        choices: Optional list of valid choices

    Returns:
        str: The user's input response
    """

    if choices:
        console.print(f"\n[cyan]Options: {', '.join(choices)}[/cyan]")

    if show_help:
        console.print("[dim]Press Tab for completion, ↑/↓ for history, Ctrl+R to search[/dim]")

        # Initialize readline with history and completion
        readline.parse_and_bind('tab: complete')
        def completer(text, state):
            options = [c for c in choices if c.startswith(text)]
            return options[state] if state < len(options) else None
        readline.set_completer(completer)

    # Enable emacs-style key bindings
    readline.parse_and_bind('"up": previous-history')      # Up arrow
    readline.parse_and_bind('"down": next-history')        # Down arrow
    readline.parse_and_bind('"ctrl-r": reverse-search-history') # Ctrl+R
    readline.parse_and_bind('"ctrl-a": beginning-of-line') # Ctrl+A
    readline.parse_and_bind('"ctrl-e": end-of-line')       # Ctrl+E
    readline.parse_and_bind('"ctrl-k": kill-line')         # Ctrl+K
    readline.parse_and_bind('"ctrl-u": unix-line-discard') # Ctrl+U

    try:
        response = Prompt.ask(f"[bold cyan]> {message}[/bold cyan]\n")
        if response.strip():
            readline.add_history(response)
            # Save history immediately after each command
            history_file = config.workspace_dir / '.janito' / 'command_history'
            readline.write_history_file(str(history_file))
        return response
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return ""
    except EOFError:  # Ctrl+D
        console.print("\n[yellow]Exiting shell[/yellow]")
        return "/exit"
