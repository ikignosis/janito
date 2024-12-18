"""Command processor for Janito shell."""
from typing import Optional
from rich.console import Console
from .registry import CommandRegistry

class CommandProcessor:
    """Processes shell commands."""

    def __init__(self, registry: CommandRegistry) -> None:
        """Initialize command processor with registry."""
        super().__init__()
        self.console = Console()
        self.workspace_content: Optional[str] = None
        self.registry = registry

    def process_command(self, command_line: str) -> None:
        """Process a command line input."""
        command_line = command_line.strip()
        if not command_line:
            return

        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command := self.registry.get_command(cmd):
            command.handler(args)
        else:
            # Treat as request command
            if request_cmd := self.registry.get_command("/request"):
                request_cmd.handler(command_line)
            else:
                self.console.print("[red]Error: Request command not registered[/red]")