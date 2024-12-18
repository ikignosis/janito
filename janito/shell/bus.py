"""Command bus implementation for Janito shell."""
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class Command:
    """Command message for command bus."""
    name: str
    args: str

class CommandBus:
    """Simple command bus implementation."""
    _instance = None
    _handlers: Dict[str, Callable[[Command], None]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def register_handler(self, command_name: str, handler: Callable[[Command], None]) -> None:
        """Register a handler for a command."""
        self._handlers[command_name] = handler

    def handle(self, command: Command) -> None:
        """Handle a command by dispatching to appropriate handler."""
        if handler := self._handlers.get(command.name):
            handler(command)
        else:
            raise ValueError(f"No handler registered for command: {command.name}")