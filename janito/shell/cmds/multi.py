"""
/multi command handler - toggles multiline mode for input.
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
            self._toggle_multiline(shell)
            return True
        return False
    
    def _toggle_multiline(self, shell) -> None:
        """Toggle multiline mode and print status."""
        # Get current state, toggle it, and apply to shell
        new_state = not getattr(shell, 'multiline_mode', False)
        shell.multiline_mode = new_state
        
        # Recreate the session with new multiline setting
        shell.session = shell._create_session(multiline=new_state)
        
        status = "enabled" if new_state else "disabled"
        print(f"\n[Multiline mode {status}] - Use (ESC ENTER to submit) to submit in multiline mode")
        print()


# Register this handler
_handler = MultiCmdHandler()
register_command(_handler)
