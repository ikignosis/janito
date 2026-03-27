"""
Base command handler class.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..interactive import InteractiveShell


class CmdHandler(ABC):
    """
    Abstract base class for shell command handlers.
    
    Command handlers can register themselves and will be automatically
    discovered and used by the interactive shell.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The command name (e.g., '/config')."""
        pass
    
    @abstractmethod
    def handle(self, shell: "InteractiveShell", user_input: str) -> bool:
        """
        Handle a command.
        
        Args:
            shell: The interactive shell instance
            user_input: The raw user input
            
        Returns:
            True if the command was handled, False otherwise
        """
        pass
    
    def on_command(self, shell: "InteractiveShell", user_input: str) -> None:
        """
        Called when this command is invoked.
        Override this to provide command-specific behavior.
        
        Args:
            shell: The interactive shell instance
            user_input: The raw user input
        """
        pass
