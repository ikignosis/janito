"""Command definitions for Janito shell."""
from typing import Dict, Optional
from dataclasses import dataclass
from rich.console import Console
from janito.common import progress_send_message

@dataclass
class Command:
    """Represents a shell command."""
    name: str
    description: str
    usage: Optional[str]
    handler: callable

    def execute(self, args: str) -> None:
        """Execute the command with given arguments."""
        self.handler(args)

def handle_request(args: str) -> None:
    """Handle a change request."""
    if not args:
        Console().print("[red]Error: Change request required[/red]")
        return
    from janito.cli.commands import handle_request as cli_handle_request
    cli_handle_request(args)

def handle_exit(_: str) -> None:
    """Handle exit command."""
    raise EOFError()

def get_commands() -> Dict[str, Command]:
    """Get the dictionary of available commands."""
    commands = {
        "/request": Command(
            "/request",
            "Submit a change request",
            "/request <change request text>",
            handle_request
        ),
        "/ask": Command(
            "/ask",
            "Ask a question about the codebase",
            "/ask <question>",
            handle_ask
        ),
        "/quit": Command(
            "/quit",
            "Exit the shell",
            None,
            handle_exit
        ),
        "/help": Command(
            "/help",
            "Show help for commands",
            "/help [command]",
            handle_help
        ),
        "/include": Command(
            "/include",
            "Set paths to include in analysis",
            "/include <path1> [path2 ...]",
            handle_include
        ),
        "/rinclude": Command(
            "/rinclude",
            "Set paths to include recursively in analysis",
            "/rinclude <path1> [path2 ...]",
            handle_rinclude
        )
    }

    # Add aliases without / prefix
    aliases = {
        "quit": commands["/quit"],
        "help": commands["/help"]
    }

    return commands | aliases

def handle_help(args: str) -> None:
    """Handle help command."""
    from janito.shell.processor import CommandProcessor
    processor = CommandProcessor()
    processor.show_help(args.strip() if args else None)
from pathlib import Path
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit import PromptSession
from janito.config import config
from janito.scan import collect_files_content
from janito.scan.analysis import analyze_workspace_content

def handle_include(args: str) -> None:
    """Handle include command with path completion."""
    console = Console()
    session = PromptSession()
    completer = PathCompleter()

    # If no args provided, prompt with completion
    if not args:
        try:
            args = session.prompt("Enter paths (space separated): ", completer=completer)
        except (KeyboardInterrupt, EOFError):
            return

    # Split paths and handle empty input
    paths = [p.strip() for p in args.split() if p.strip()]
    if not paths:
        console.print("[red]Error: At least one path required[/red]")
        return

    # Convert to Path objects relative to workdir
    resolved_paths = []
    for path_str in paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = config.workdir / path
        resolved_paths.append(path.resolve())

    # Update config and refresh workspace content
    config.set_include(resolved_paths)

    # Update workspace content
    from janito.shell.processor import CommandProcessor
    processor = CommandProcessor()
    content = collect_files_content(resolved_paths)
    analyze_workspace_content(content)
    processor.workspace_content = content

    console.print(f"[green]Updated include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")
def handle_rinclude(args: str) -> None:
    """Handle rinclude command with recursive path scanning."""
    console = Console()
    session = PromptSession()
    completer = PathCompleter(only_directories=True)  # Only allow directory paths

    # If no args provided, prompt with completion
    if not args:
        try:
            args = session.prompt("Enter directory paths (space separated): ", completer=completer)
        except (KeyboardInterrupt, EOFError):
            return

    # Split paths and handle empty input
    paths = [p.strip() for p in args.split() if p.strip()]
    if not paths:
        console.print("[red]Error: At least one path required[/red]")
        return

    # Convert to Path objects relative to workdir
    resolved_paths = []
    for path_str in paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = config.workdir / path
        resolved_paths.append(path.resolve())

    # Update config with both include and recursive paths
    config.set_recursive(resolved_paths)
    config.set_include(resolved_paths)

    # Update workspace content
    from janito.shell.processor import CommandProcessor
    processor = CommandProcessor()
    content = collect_files_content(resolved_paths)
    analyze_workspace_content(content)
    processor.workspace_content = content

    console.print(f"[green]Updated recursive include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")
def handle_ask(args: str) -> None:
    """Handle ask command."""
    if not args:
        Console().print("[red]Error: Question required[/red]")
        return
    from janito.cli.commands import handle_ask as cli_handle_ask
    cli_handle_ask(args)