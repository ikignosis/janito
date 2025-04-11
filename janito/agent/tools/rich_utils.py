from rich.console import Console
from rich.text import Text

console = Console()

def print_info(message: str):
    console.print(message, style="cyan")

def print_success(message: str):
    console.print(message, style="bold green")

def print_error(message: str):
    console.print(message, style="bold red")

def print_warning(message: str):
    console.print(message, style="yellow")

def print_magenta(message: str):
    console.print(message, style="magenta")

def print_bash_stdout(message: str):
    console.print(message, style="bold white on blue")

def print_bash_stderr(message: str):
    console.print(message, style="bold white on red")

def format_path(path: str) -> Text:
    return Text(path, style="cyan")

def format_number(number) -> Text:
    return Text(str(number), style="magenta")
