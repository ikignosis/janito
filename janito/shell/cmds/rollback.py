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
            # Responses API mode: the conversation lives outside
            # messages_history. Stateless endpoints (e.g. DeepSeek) keep the
            # history client-side in conversation_items; server-side endpoints
            # (e.g. OpenAI) keep it behind previous_response_id.
            conversation_items = getattr(shell, "conversation_items", None)
            if conversation_items is not None:
                conversation_checkpoint = getattr(shell, "conversation_checkpoint", 0)
                if conversation_checkpoint < len(conversation_items):
                    del conversation_items[conversation_checkpoint:]
                    print(
                        "Rolled back: conversation history truncated "
                        "(stateless Responses API)."
                    )
                    return
            if getattr(shell, "previous_response_id", None) is not None:
                shell.previous_response_id = None
                print("Rolled back: server-side conversation reset (Responses API).")
                return
            print("Nothing to rollback. History is already at the checkpoint.")
            return

        removed = current_len - checkpoint
        del shell.messages_history[checkpoint:]
        print(
            f"Rolled back {removed} message(s). History now has {len(shell.messages_history)} message(s)."
        )


# Register this handler
_handler = RollbackCmdHandler()
register_command(_handler)
