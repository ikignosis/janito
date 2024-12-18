"""Command handlers for Janito shell."""
from pathlib import Path
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.shortcuts import clear as ptk_clear
from janito.config import config
from janito.scan import collect_files_content
from janito.scan.analysis import analyze_workspace_content
from .registry import CommandRegistry, get_path_completer

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

def handle_clear(_: str) -> None:
    """Handle clear command to clear terminal screen."""
    ptk_clear()

def handle_ask(args: str) -> None:
    """Handle ask command."""
    if not args:
        Console().print("[red]Error: Question required[/red]")
        return
    from janito.cli.commands import handle_ask as cli_handle_ask
    cli_handle_ask(args)

def handle_help(args: str) -> None:
    """Handle help command."""
    console = Console()
    registry = CommandRegistry()

    command = args.strip() if args else None
    if command and (cmd := registry.get_command(command)):
        console.print(f"\n[bold]{command}[/bold]: {cmd.description}")
        if cmd.usage:
            console.print(f"Usage: {cmd.usage}")
        return

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    for name, cmd in sorted(registry.get_commands().items()):
        table.add_row(name, cmd.description)

    console.print(table)

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

    paths = [p.strip() for p in args.split() if p.strip()]
    if not paths:
        console.print("[red]Error: At least one path required[/red]")
        return

    resolved_paths = []
    for path_str in paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = config.workdir / path
        resolved_paths.append(path.resolve())

    config.set_include(resolved_paths)
    content = collect_files_content(resolved_paths)
    analyze_workspace_content(content)

    console.print(f"[green]Updated include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")

def handle_rinclude(args: str) -> None:
    """Handle rinclude command with recursive path scanning."""
    console = Console()
    session = PromptSession()
    completer = get_path_completer(only_directories=True)

    if not args:
        try:
            args = session.prompt("Enter directory paths (space separated): ", completer=completer)
        except (KeyboardInterrupt, EOFError):
            return

    paths = [p.strip() for p in args.split() if p.strip()]
    if not paths:
        console.print("[red]Error: At least one path required[/red]")
        return

    resolved_paths = []
    for path_str in paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = config.workdir / path
        resolved_paths.append(path.resolve())

    config.set_recursive(resolved_paths)
    config.set_include(resolved_paths)
    content = collect_files_content(resolved_paths)
    analyze_workspace_content(content)

    console.print(f"[green]Updated recursive include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")
