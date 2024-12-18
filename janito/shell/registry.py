"""Command registry for Janito shell."""
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from prompt_toolkit.completion import PathCompleter, Completer

@dataclass
class Command:
    """Represents a shell command."""
    name: str
    description: str
    usage: Optional[str]
    handler: Callable[[str], None]
    completer: Optional[Callable[[], Completer]] = None

    def execute(self, args: str) -> None:
        """Execute the command with given arguments."""
        self.handler(args)

    def get_completer(self) -> Optional[Completer]:
        """Get command completer if available."""
        return self.completer() if self.completer else None

def get_path_completer(only_directories: bool = False) -> PathCompleter:
    """Get a path completer instance.
    
    Args:
        only_directories: If True, only complete directory paths.
                        If False, complete both files and directories.
    """
    return PathCompleter(
        only_directories=only_directories,
        min_input_len=0,  # Start completing immediately
        get_paths=None    # Use default path discovery
    )

class CommandRegistry:
    """Global command registry."""
    _instance = None
    _commands: Dict[str, Command] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
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

    def get_completer(self, command_name: str) -> Optional[Completer]:
        """Get completer for a command if available."""
        if command := self.get_command(command_name):
            return command.get_completer()
        return None