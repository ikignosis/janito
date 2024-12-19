"""Command system for Janito shell."""
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear as ptk_clear
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.document import Document
from pathlib import Path
from janito.config import config
from janito.workspace import workset  # Updated import
from janito.workspace.analysis import analyze_workspace_content
from .registry import CommandRegistry, Command, get_path_completer

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
    """Handle clear command."""
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
    else:
        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        for name, cmd in sorted(registry.get_commands().items()):
            table.add_row(name, cmd.description)

        console.print(table)

def handle_include(args: str) -> None:
    """Handle include command."""
    console = Console()
    session = PromptSession()

    if not args:
        try:
            args = session.prompt("Enter paths (space separated): ")
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
            path = config.workspace_dir / path
        resolved_paths.append(path.resolve())

    workset.include(resolved_paths)
    workset.show()

    console.print("[green]Updated include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")

def handle_rinclude(args: str) -> None:
    """Handle recursive include command."""
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
            path = config.workspace_dir / path
        resolved_paths.append(path.resolve())

    workset.recursive(resolved_paths)
    workset.include(resolved_paths)  # Add recursive paths to include paths
    workset.refresh()
    workset.show()

    console.print("[green]Updated recursive include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")

def register_commands(registry: CommandRegistry) -> None:
    """Register all available commands."""
    # Register main commands
    registry.register(Command("/clear", "Clear the terminal screen", None, handle_clear))
    registry.register(Command("/request", "Submit a change request", "/request <change request text>", handle_request))
    registry.register(Command("/ask", "Ask a question about the codebase", "/ask <question>", handle_ask))
    registry.register(Command("/quit", "Exit the shell", None, handle_exit))
    registry.register(Command("/help", "Show help for commands", "/help [command]", handle_help))
    registry.register(Command("/include", "Set paths to include in analysis", "/include <path1> [path2 ...]", handle_include, get_path_completer()))
    registry.register(Command("/rinclude", "Set paths to include recursively", "/rinclude <path1> [path2 ...]", handle_rinclude, get_path_completer(True)))

    # Register aliases
    registry.register_alias("clear", "/clear")
    registry.register_alias("quit", "/quit")
    registry.register_alias("help", "/help")
    registry.register_alias("/inc", "/include")
    registry.register_alias("/rinc", "/rinclude")