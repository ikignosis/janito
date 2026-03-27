"""
/exit command handler - exits the chat session.
"""

from .base import CmdHandler
from .registry import register_command


class ExitCmdHandler(CmdHandler):
    """Command handler for /exit command."""
    
    @property
    def name(self) -> str:
        return "/exit"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /exit command."""
        if user_input.lower() == self.name.lower():
            shell.exit_requested = True
            return True
        return False


# Register this handler
_handler = ExitCmdHandler()
register_command(_handler)
