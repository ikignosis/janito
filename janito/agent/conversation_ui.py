"""
UI helpers for conversation (spinner, verbose output).
"""

from rich.console import Console


def show_spinner(message, func, *args, **kwargs):
    console = Console()
    with console.status(message, spinner="dots") as status:
        result = func(*args, **kwargs)
        status.stop()
        return result


def print_verbose_event(event):
    print(f"[EVENT] {event}")
