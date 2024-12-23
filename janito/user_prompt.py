from typing import List, Optional
import readline
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def prompt_user(message: str, choices: List[str] = None) -> str:
    """Display a simple user prompt with readline support and optional choices.

    Args:
        message: The prompt message to display
        choices: Optional list of valid choices

    Returns:
        str: The user's input response
    """
    if choices:
        console.print(f"\n[cyan]Options: {', '.join(choices)}[/cyan]")

        # Initialize readline with history and completion
        readline.parse_and_bind('tab: complete')
        def completer(text, state):
            options = [c for c in choices if c.startswith(text)]
            return options[state] if state < len(options) else None
        readline.set_completer(completer)

    try:
        response = Prompt.ask(f"[bold cyan]> {message}[/bold cyan]")
        if response.strip():
            readline.add_history(response)
        return response
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return ""