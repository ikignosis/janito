"""
/history command handler - displays the contents of message_history.
"""

import json
from .base import CmdHandler
from .registry import register_command


class HistoryCmdHandler(CmdHandler):
    """Command handler for /history command."""
    
    @property
    def name(self) -> str:
        return "/history"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /history command."""
        if user_input.lower() == self.name.lower():
            self._print_history(shell)
            return True
        return False
    
    def _print_history(self, shell) -> None:
        """Print the contents of the message history."""
        print()
        print("=" * 50)
        print("Message History")
        print("=" * 50)
        
        if not shell.messages_history:
            print("  (empty)")
        else:
            for i, msg in enumerate(shell.messages_history):
                if isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                else:
                    print(msg)
                    role = msg.role
                    content = msg.content

                # Truncate long content for display
                if len(content) > 200:
                    content_preview = content[:200] + "..."
                else:
                    content_preview = content
                
                # Replace newlines for cleaner display
                content_preview = content_preview.replace("\n", "\\n")
                
                print(f"  [{i}] {role}: {content_preview}")
        
        print("=" * 50)
        print()


# Register this handler
_handler = HistoryCmdHandler()
register_command(_handler)
