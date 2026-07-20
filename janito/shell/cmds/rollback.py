"""
/rollback command handler - truncates message_history back to the last checkpoint.
"""

from .base import CmdHandler
from .registry import register_command


class RollbackCmdHandler(CmdHandler):
    """Command handler for /rollback command."""
    
    @property
    def name(self) -> str:
        return "/rollback"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /rollback command."""
        if user_input.lower().strip() == self.name:
            self._do_rollback(shell)
            return True
        return False
    
    def _do_rollback(self, shell) -> None:
        """Truncate messages_history back to the last checkpoint."""
        checkpoint = getattr(shell, "history_checkpoint", 0)
        current_len = len(shell.messages_history)
        
        if current_len <= checkpoint:
            print("Nothing to rollback. History is already at the checkpoint.")
            return
        
        removed = current_len - checkpoint
        del shell.messages_history[checkpoint:]
        print(f"Rolled back {removed} message(s). History now has {len(shell.messages_history)} message(s).")


# Register this handler
_handler = RollbackCmdHandler()
register_command(_handler)
