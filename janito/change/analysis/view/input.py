"""Terminal UI input components for analysis."""

from typing import Dict
from rich.console import Console
from rich.prompt import Prompt

from ..options import AnalysisOption

def prompt_user(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default value."""
    return Prompt.ask(prompt, default=default)

def get_option_selection(options: Dict[str, AnalysisOption]) -> str:
    """Get user selection from available options."""
    valid_options = sorted(options.keys())
    while True:
        choice = prompt_user(
            f"Select an option [{'/'.join(valid_options)}]",
            default=valid_options[0]
        ).upper()
        if choice in valid_options:
            return choice
        console = Console()
        console.print(f"[red]Invalid option. Please choose from {', '.join(valid_options)}[/red]")