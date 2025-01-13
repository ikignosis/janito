from typing import List, Optional
import readline
from rich.console import Console
from rich.prompt import Prompt

console = Console()
import atexit
from pathlib import Path
from janito.config import config

SHORTCUTS_INFO = """
Available keyboard shortcuts:
  Up/Down : Navigate command history
  Ctrl+R  : Reverse search in history
  Tab     : Auto-complete (when choices available)
  Ctrl+A  : Move cursor to start of line
  Ctrl+E  : Move cursor to end of line
  Ctrl+K  : Clear line after cursor
  Ctrl+U  : Clear line before cursor
  Ctrl+D  : Exit shell
"""

def show_shortcuts():
    """Display available keyboard shortcuts."""
    print("\nKeyboard Shortcuts:")
    print("-" * 20)
    print(SHORTCUTS_INFO)
    print("-" * 20)

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

    # Save history on exit
    atexit.register(readline.write_history_file, str(history_file))

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
        return response
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return ""
    except EOFError:  # Ctrl+D
        console.print("\n[yellow]Exiting shell[/yellow]")
        return "/exit"
