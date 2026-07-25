"""
/multi command handler - enables multiline mode for the next prompt only.
"""

from .base import CmdHandler
from .registry import register_command


class MultiCmdHandler(CmdHandler):
    """Command handler for /multi command."""
    
    @property
    def name(self) -> str:
        return "/multi"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /multi command."""
        if user_input.strip().lower() == self.name.lower():
            self._enable_multiline(shell)
            return True
        return False
    
    def _enable_multiline(self, shell) -> None:
        """Enable multiline mode for the next prompt (single use)."""
        shell.multiline_mode = True
        
        # Recreate the session with multiline enabled
        shell.session = shell._create_session(multiline=True)
        
        print("\n[Multiline mode enabled for next prompt] - Use ESC ENTER to submit")
        print()


# Register this handler
_handler = MultiCmdHandler()
register_command(_handler)
