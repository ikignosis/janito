"""Command registry and validation system for Janito shell."""
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from prompt_toolkit.completion import PathCompleter

@dataclass
class Command:
    """Command definition with handler and metadata."""
    name: str
    description: str
    usage: Optional[str]
    handler: Callable[[str], None]
    completer: Optional[Any] = None

class CommandRegistry:
    """Centralized command registry with validation."""
    def __init__(self):
        """Initialize registry."""
        if not hasattr(self, '_commands'):
            self._commands = {}


    def register(self, command: Command) -> None:
        """Register a command with validation."""
        if command.name in self._commands:
            raise ValueError(f"Command '{command.name}' already registered")
        if not callable(command.handler):
            raise ValueError(f"Handler for command '{command.name}' must be callable")
        self._commands[command.name] = command

    def register_alias(self, alias: str, command_name: str) -> None:
        """Register an alias for an existing command."""
        if alias in self._commands:
            raise ValueError(f"Alias '{alias}' already registered")
        if command := self.get_command(command_name):
            self._commands[alias] = command
        else:
            raise ValueError(f"Command '{command_name}' not found")

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self._commands.get(name)

    def get_commands(self) -> Dict[str, Command]:
        """Get all registered commands."""
        return self._commands.copy()

    def validate_command(self, command: Command) -> None:
        """Validate command properties."""
        if not command.name:
            raise ValueError("Command name cannot be empty")
        if not command.description:
            raise ValueError(f"Command '{command.name}' must have a description")
        if not callable(command.handler):
            raise ValueError(f"Command '{command.name}' handler must be callable")

def get_path_completer(only_directories: bool = False) -> PathCompleter:
    """Get a configured path completer."""
    return PathCompleter(only_directories=only_directories)