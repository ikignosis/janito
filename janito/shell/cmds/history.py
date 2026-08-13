"""
/history command handler - displays the contents of message_history.
"""


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
        """Print the contents of the message history as a rich table."""
        from rich.console import Console
        from rich.table import Table

        if not shell.messages_history:
            Console(markup=False).print("(empty)")
            return

        table = Table(
            title="Message History",
            title_style="bold",
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim", no_wrap=True)
        table.add_column("Role", style="green", no_wrap=True)
        table.add_column("Content", overflow="fold")

        for i, msg in enumerate(shell.messages_history):
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content") or ""
            else:
                role = msg.role
                content = msg.content or ""

            # Truncate long content for display
            if len(content) > 200:
                content_preview = content[:200] + "..."
            else:
                content_preview = content

            # Replace newlines for cleaner display
            content_preview = content_preview.replace("\n", "\\n")

            table.add_row(str(i), role, content_preview)

        Console(markup=False).print(table)


# Register this handler
_handler = HistoryCmdHandler()
register_command(_handler)
