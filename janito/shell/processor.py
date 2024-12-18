"""Command processor for Janito shell."""
from typing import Dict, Callable, List, Optional
from prompt_toolkit.completion import Completer
from rich.console import Console
from rich.table import Table
from janito.scan.analysis import analyze_workspace_content
from .commands import register_commands
from .registry import CommandRegistry

class CommandProcessor:
    """Processes shell commands and manages command registry."""

    def __init__(self):
        register_commands()
        self.registry = CommandRegistry()
        self.console = Console()
        self.workspace_content: Optional[str] = None

    def _validate_commands(self) -> None:
        """Validate command registry for alias conflicts."""
        commands = self.registry.get_commands()
        seen = set()
        for cmd_name in commands:
            if cmd_name in seen:
                raise ValueError(f"Command alias conflict: {cmd_name} is already registered")
            seen.add(cmd_name)

    def get_command_completer(self, command_name: str) -> Optional[Completer]:
        """Get completer for a command if available."""
        return self.registry.get_completer(command_name)

    def process_command(self, command_line: str) -> None:
        """Process a command line input.

        Args:
            command_line: The command line to process
        """
        command_line = command_line.strip()
        if not command_line:
            return

        # Check if it starts with a known command or alias
        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()

        if command := self.registry.get_command(cmd):
            args = parts[1] if len(parts) > 1 else ""
            command.execute(args)
        else:
            # Treat entire input as a request
            request_cmd = self.registry.get_command("/request")
            if request_cmd:
                request_cmd.execute(command_line)
            else:
                self.console.print("[red]Error: Request command not registered[/red]")

    def show_help(self, command: Optional[str] = None) -> None:
        """Show help for commands.

        Args:
            command: Optional specific command to show help for
        """
        if command and (cmd := self.registry.get_command(command)):
            self.console.print(f"\n[bold]{command}[/bold]: {cmd.description}")
            if cmd.usage:
                self.console.print(f"Usage: {cmd.usage}")
            return

        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        for name, cmd in sorted(self.registry.get_commands().items()):
            table.add_row(name, cmd.description)

        self.console.print(table)