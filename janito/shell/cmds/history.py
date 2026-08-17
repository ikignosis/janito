"""
/history command handler - displays the contents of the conversation history.
"""

from __future__ import annotations

from typing import Any

from .base import CmdHandler
from .registry import register_command


def _content_text(content: Any) -> str:
    """Extract the plain text of a Responses ``message`` content block.

    Responses content is a list of typed blocks (``input_text`` /
    ``output_text`` / ``refusal`` / ...).  ``str`` content is returned as-is
    (defensive; the real items always use the block list form).
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict):
            text = block.get("text")
            if text:
                parts.append(text)
    return "".join(parts)


def _responses_item_to_row(item: dict[str, Any]) -> tuple[str, str]:
    """Convert one Responses input item into a ``(role, content)`` display row.

    Stateless Responses providers (e.g. DeepSeek) keep the full conversation
    client-side as Responses input items: ``message`` items (system / user /
    assistant) plus ``function_call`` / ``function_call_output`` items for the
    tool-call rounds.  Each becomes a row so ``/history`` reads like the
    Completions history table.
    """
    item_type = item.get("type", "unknown")
    if item_type == "message":
        return item.get("role", "unknown"), _content_text(item.get("content"))
    if item_type == "function_call":
        arguments = item.get("arguments") or ""
        return "function_call", f"{item.get('name', '')}({arguments})"
    if item_type == "function_call_output":
        return "function_call_output", str(item.get("output") or "")
    if item_type == "reasoning":
        return "reasoning", str(item.get("summary") or item.get("text") or "")
    return item_type, str(item)


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

    def _history_rows(self, shell) -> list[tuple[str, str]]:
        """Return ``(role, content)`` rows from the effective history source.

        The history lives in different places depending on the API type:

        - Completions / Anthropic / DashScope: ``shell.messages_history`` holds
          the whole conversation (system + user + assistant).
        - Stateless Responses (e.g. DeepSeek): the full conversation is kept
          client-side in ``shell.conversation_items`` as Responses input items
          (with the system prompt folded in on the first turn); ``messages_history``
          then only ever holds the system prompt, so prefer the items.
        - Server-side Responses (e.g. OpenAI): the history is stored on the
          server; ``messages_history`` holds the system prompt and
          ``conversation_items`` may hold pending (Enter-cancelled) messages
          that are not yet part of a completed server response.
        """
        conversation_items = getattr(shell, "conversation_items", None) or []
        if conversation_items and conversation_items[0].get("role") == "system":
            # Stateless Responses: the items already include the system prompt.
            return [_responses_item_to_row(item) for item in conversation_items]

        rows: list[tuple[str, str]] = []
        for msg in shell.messages_history:
            if isinstance(msg, dict):
                rows.append((msg.get("role", "unknown"), msg.get("content") or ""))
            else:
                rows.append((msg.role, msg.content or ""))
        if conversation_items:
            # Server-side Responses: pending user messages of an Enter-cancelled
            # turn, appended after the system prompt.
            rows.extend(_responses_item_to_row(item) for item in conversation_items)
        return rows

    def _print_history(self, shell) -> None:
        """Print the contents of the message history as a rich table."""
        from rich.console import Console
        from rich.table import Table

        rows = self._history_rows(shell)
        if not rows:
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

        for i, (role, content) in enumerate(rows):
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
