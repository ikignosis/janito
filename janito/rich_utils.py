"""
Utilities for working with the Rich library.
"""

from rich.markdown import Markdown
from rich.text import Text
from rich.console import Console


def print_markdown(console: Console, message: str):
    console.print(Markdown(message))


def print_info(console: Console, message: str):
    console.print(message, style="cyan", end="")


def print_success(console: Console, message: str):
    console.print(message, style="bold green", end="\n")


def print_error(console: Console, message: str):
    console.print(message, style="bold red", end="\n")


def print_warning(console: Console, message: str):
    console.print(message, style="bold yellow", end="\n")


def print_magenta(console: Console, message: str):
    console.print(message, style="magenta", end="\n")


def print_stdout(console: Console, message: str):
    console.print(
        Text(message, style="on #003300", no_wrap=True, overflow=None), end=""
    )


def print_stderr(console: Console, message: str):
    console.print(
        Text(message, style="on #330000", no_wrap=True, overflow=None), end=""
    )
