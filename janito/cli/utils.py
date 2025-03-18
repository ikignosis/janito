"""
Utility functions for the CLI module.
"""
import platform
from rich.console import Console

console = Console()

def get_stdin_termination_hint():
    """
    Returns a user-friendly message about how to terminate stdin input
    based on the current platform.
    
    Returns:
        str: A message with the key sequence to terminate stdin input
    """
    system = platform.system()
    
    if system == "Windows":
        return "[bold yellow]Press Ctrl+Z followed by Enter to terminate input[/bold yellow]"
    else:  # Unix-like systems (Linux, macOS)
        return "[bold yellow]Press Ctrl+D to terminate input[/bold yellow]"