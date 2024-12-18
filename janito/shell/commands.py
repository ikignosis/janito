"""Command system for Janito shell."""
from dataclasses import dataclass
from typing import Optional, Callable, Dict
from pathlib import Path
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear as ptk_clear
from janito.config import config
from janito.workspace import collect_files_content
from janito.workspace.analysis import analyze_workspace_content

@dataclass
class Command:
    """Command definition with handler."""
    name: str
    description: str
    usage: Optional[str]
    handler: Callable[[str], None]

class CommandSystem:
    """Centralized command management system."""
    _instance = None
    _commands: Dict[str, Command] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._commands = {}
        return cls._instance

    def register(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.name] = command

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self._commands.get(name)

    def get_commands(self) -> Dict[str, Command]:
        """Get all registered commands."""
        return self._commands.copy()

    def register_alias(self, alias: str, command_name: str) -> None:
        """Register an alias for a command."""
        if command := self.get_command(command_name):
            if alias in self._commands:
                raise ValueError(f"Alias '{alias}' already registered")
            self._commands[alias] = command

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
    system = CommandSystem()

    command = args.strip() if args else None
    if command and (cmd := system.get_command(command)):
        console.print(f"\n[bold]{command}[/bold]: {cmd.description}")
        if cmd.usage:
            console.print(f"Usage: {cmd.usage}")
        return

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    for name, cmd in sorted(system.get_commands().items()):
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
            path = config.workdir / path
        resolved_paths.append(path.resolve())

    config.set_include(resolved_paths)
    content = collect_files_content(resolved_paths)
    analyze_workspace_content(content)

    console.print("[green]Updated include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.document import Document

def handle_rinclude(args: str) -> None:
    """Handle recursive include command."""
    console = Console()
    session = PromptSession()
    completer = PathCompleter(only_directories=True)

    try:
        if not args:
            args = session.prompt("Enter directory paths (space separated): ", completer=completer)
        else:
            # For partial paths, show completion options
            doc = Document(args)
            completions = list(completer.get_completions(doc, None))
            if completions:
                # If single completion, use it directly
                if len(completions) == 1:
                    args = completions[0].text
                else:
                    # Show available completions
                    console.print("\nAvailable directories:")
                    for comp in completions:
                        console.print(f"  {comp.text}")
                    return
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

    console.print("[green]Updated recursive include paths:[/green]")
    for path in resolved_paths:
        console.print(f"  {path}")

def register_commands() -> None:
    """Register all available commands."""
    system = CommandSystem()

    # Register main commands
    system.register(Command("/clear", "Clear the terminal screen", None, handle_clear))
    system.register(Command("/request", "Submit a change request", "/request <change request text>", handle_request))
    system.register(Command("/ask", "Ask a question about the codebase", "/ask <question>", handle_ask))
    system.register(Command("/quit", "Exit the shell", None, handle_exit))
    system.register(Command("/help", "Show help for commands", "/help [command]", handle_help))
    system.register(Command("/include", "Set paths to include in analysis", "/include <path1> [path2 ...]", handle_include))
    system.register(Command("/rinclude", "Set paths to include recursively", "/rinclude <path1> [path2 ...]", handle_rinclude))

    # Register aliases
    system.register_alias("clear", "/clear")
    system.register_alias("quit", "/quit")
    system.register_alias("help", "/help")
    system.register_alias("/inc", "/include")
    system.register_alias("/rinc", "/rinclude")