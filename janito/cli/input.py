from typing import Optional
from rich.console import Console
import sys

def read_input() -> Optional[str]:
    """Read input from stdin until EOF"""
    console = Console()
    console.print("[dim]Enter your request (press Ctrl+D when finished):[/dim]")
    try:
        return sys.stdin.read().strip()
    except KeyboardInterrupt:
        return None