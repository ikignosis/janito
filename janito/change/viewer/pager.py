from rich.console import Console
import shutil
from typing import Optional

def clear_last_line(console: Console):
    """Clear the last line in the terminal"""
    console.print("\r\033[1A\033[2K", end="")

def wait_for_enter(console: Console):
    """Wait for ENTER key press to continue"""
    console.print("\n[dim]Press ENTER to continue...[/dim]")
    try:
        input()
        clear_last_line(console)
    except KeyboardInterrupt:
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
    term_height = shutil.get_terminal_size().lines
    margin = 5  # Add margin to prevent too early paging
    available_height = term_height - margin  # Leave more room at start

    # If we know the upcoming content height and it won't fit, page now
    if content_height and (height + content_height > available_height):
        wait_for_enter(console)
        return 0

    # Otherwise check if current height exceeds threshold
    # Add extra room for first page
    if height >= available_height - (3 if height < term_height else 0):
        wait_for_enter(console)
        return 0

    return height