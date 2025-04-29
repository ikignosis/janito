"""
Utilities for working with the Rich library.
"""

from rich.console import Console


def print_info(console: Console, message: str):
    console.print(message, style="cyan", end="")


def print_error(console: Console, message: str):
    console.print(message, style="bold red", end="\n")


def print_warning(console: Console, message: str):
    console.print(message, style="bold yellow", end="\n")


def print_magenta(console: Console, message: str):
    console.print(message, style="magenta", end="\n")
