"""Command processor for Janito shell."""
from typing import Optional
from rich.console import Console
from .commands import CommandSystem, register_commands

class CommandProcessor:
    """Processes shell commands."""

    def __init__(self):
        self.console = Console()
        self.workspace_content: Optional[str] = None
        register_commands()

    def process_command(self, command_line: str) -> None:
        """Process a command line input."""
        command_line = command_line.strip()
        if not command_line:
            return

        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        system = CommandSystem()
        if command := system.get_command(cmd):
            # Special handling for /rinc command to support interactive completion
            if cmd in ["/rinc", "/rinclude"] and args:
                from prompt_toolkit.completion import PathCompleter
                from prompt_toolkit.document import Document

                completer = PathCompleter(only_directories=True)
                doc = Document(args)
                completions = list(completer.get_completions(doc, None))

                if completions:
                    if len(completions) == 1:
                        # Single completion - use it
                        args = completions[0].text
                    else:
                        # Show available completions
                        self.console.print("\nAvailable directories:")
                        for comp in completions:
                            self.console.print(f"  {comp.text}")
                        return

            command.handler(args)
        else:
            # Treat as request command
            if request_cmd := system.get_command("/request"):
                request_cmd.handler(command_line)
            else:
                self.console.print("[red]Error: Request command not registered[/red]")