"""
Utilities for working with the Rich library.
"""

from rich.console import Console
from typing import Optional


class RichPrinter:
    """
    Utility class for printing styled messages using the Rich library.

    Args:
        console (Optional[Console]): An optional Rich Console instance. If not provided, a default Console will be created.

    Methods:
        print_info(message: str)
            Print an informational message in cyan (no newline at end).

        print_error(message: str)
            Print an error message in bold red.

        print_warning(message: str)
            Print a warning message in bold yellow.

        print_magenta(message: str)
            Print a message in magenta.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def print_info(self, message: str):
        self.console.print(message, style="cyan", end="")

    def print_error(self, message: str):
        self.console.print(message, style="bold red", end="\n")

    def print_warning(self, message: str):
        self.console.print(message, style="bold yellow", end="\n")

    def print_magenta(self, message: str):
        self.console.print(message, style="magenta", end="\n")
