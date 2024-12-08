from typing import Callable, Dict
from dataclasses import dataclass

@dataclass
class Command:
    name: str
    handler: Callable
    help_text: str

class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        
    def register(self, name: str, help_text: str):
        def decorator(handler: Callable):
            self._commands[name] = Command(name, handler, help_text)
            return handler
        return decorator
        
    def get_command(self, name: str) -> Command:
        return self._commands.get(name)
        
    def get_all_commands(self) -> Dict[str, Command]:
        return self._commands

registry = CommandRegistry()
