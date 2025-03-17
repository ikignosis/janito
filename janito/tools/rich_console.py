"""
Utility module for rich console printing in tools.
"""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional

# Create a shared console instance
console = Console()

def print_info(message: str, title: Optional[str] = None):
    """
    Print an informational message with rich formatting.
    
    Args:
        message: The message to print
        title: Optional title for the panel
    """
    text = Text(message)
    if title:
        console.print(Panel(text, title=title, border_style="blue"))
    else:
        console.print(text, style="blue")

def print_success(message: str, title: Optional[str] = None):
    """
    Print a success message with rich formatting.
    
    Args:
        message: The message to print
        title: Optional title for the panel
    """
    text = Text(message)
    if title:
        console.print(Panel(text, title=title, border_style="green"))
    else:
        console.print(text, style="green")

def print_error(message: str, title: Optional[str] = None):
    """
    Print an error message with rich formatting.
    
    Args:
        message: The message to print
        title: Optional title for the panel
    """
    text = Text(message)
    if title:
        console.print(Panel(text, title=title, border_style="red"))
    else:
        console.print(text, style="red")

def print_warning(message: str, title: Optional[str] = None):
    """
    Print a warning message with rich formatting.
    
    Args:
        message: The message to print
        title: Optional title for the panel
    """
    text = Text(message)
    if title:
        console.print(Panel(text, title=title, border_style="yellow"))
    else:
        console.print(text, style="yellow")