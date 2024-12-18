from rich.console import Console
import shutil
from typing import Optional

def wait_for_enter(console: Console):
    """Wait for ENTER key press to continue with progress indicator"""
    console.print("\n[yellow]More content to show[/yellow]")
    console.print("[dim]Press ENTER to continue...[/dim]", end="")
    try:
        input()
        console.print()  # Just add a newline
    except KeyboardInterrupt:
        console.print()  # Just add a newline
        raise KeyboardInterrupt

# Track current file being displayed
_current_file = None

def set_current_file(filename: str) -> None:
    """Set the current file being displayed"""
    global _current_file
    _current_file = filename

def get_current_file() -> Optional[str]:
    """Get the current file being displayed"""
    return _current_file

def check_pager(console: Console, height: int, content_height: Optional[int] = None) -> int:
    """Check if we need to pause and wait for user input

    Args:
        console: Rich console instance
        height: Current accumulated height
        content_height: Optional height of content to be displayed next

    Returns:
        New accumulated height
    """
    # Get current file being displayed
    current_file = get_current_file()
    if not current_file:
        return height

    term_height = shutil.get_terminal_size().lines
    margin = 5  # Add margin to prevent too early paging
    available_height = term_height - margin

    # Calculate total height including upcoming content
    total_height = height + (content_height or 0)

    # Only page if we're at a file boundary or content won't fit
    if total_height > available_height:
        wait_for_enter(console)
        return 0

    return height