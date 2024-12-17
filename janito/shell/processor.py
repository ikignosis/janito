"""Command processor for Janito shell."""
from typing import Dict, Callable, List, Optional
from rich.console import Console
from rich.table import Table
from janito.scan.analysis import analyze_workspace_content
from .commands import get_commands

class CommandProcessor:
    """Processes shell commands and manages command registry."""

    def __init__(self):
        self.commands = get_commands()
        self.console = Console()
        self.workspace_content: Optional[str] = None

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

        if cmd in self.commands:
            args = parts[1] if len(parts) > 1 else ""
            self.commands[cmd].execute(args)
        else:
            # Treat entire input as a request
            self.commands["/request"].execute(command_line)

    def show_help(self, command: Optional[str] = None) -> None:
        """Show help for commands.

        Args:
            command: Optional specific command to show help for
        """
        if command and command in self.commands:
            cmd = self.commands[command]
            self.console.print(f"\n[bold]{command}[/bold]: {cmd.description}")
            if cmd.usage:
                self.console.print(f"Usage: {cmd.usage}")
            return

        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        for name, cmd in sorted(self.commands.items()):
            table.add_row(name, cmd.description)

        self.console.print(table)