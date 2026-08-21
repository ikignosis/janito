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
          server; the shell keeps a display-only mirror of the completed
          turns in ``shell.mirrored_history`` (Responses input items) purely
          so /history can render the conversation, plus any pending
          (Enter-cancelled) messages in ``conversation_items`` that are not
          yet part of a completed server response.
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
        # Server-side Responses: the display-only mirror of completed turns,
        # then any pending (Enter-cancelled) messages.
        mirrored = getattr(shell, "mirrored_history", None) or []
        rows.extend(_responses_item_to_row(item) for item in mirrored)
        rows.extend(_responses_item_to_row(item) for item in conversation_items)
        return rows

    def _checkpoint_markers(self, shell, num_rows: int) -> dict[int, list[int]]:
        """Map checkpoint values to their ordinal numbers per display position.

        ``shell.history_checkpoints`` holds the number of rows /history
        would render each time a user prompt was about to be sent (see
        ``InteractiveShell._history_row_count``), so each checkpoint value
        directly names the displayed row its turn started at.  Returns
        ``{row_index: [ordinals]}`` for each position that needs a marker
        (checkpoints out of range are ignored); each checkpoint keeps its
        own ordinal (1-based position in the list).
        """
        checkpoints = getattr(shell, "history_checkpoints", None) or []
        markers: dict[int, list[int]] = {}
        for ordinal, c in enumerate(checkpoints, start=1):
            if 0 <= c <= num_rows:
                markers.setdefault(c, []).append(ordinal)
        return dict(sorted(markers.items()))

    def _print_history(self, shell) -> None:
        """Print the contents of the message history as a rich table."""
        from rich.console import Console
        from rich.table import Table

        rows = self._history_rows(shell)
        if not rows:
            Console(markup=False).print("(empty)")
            return

        markers = self._checkpoint_markers(shell, len(rows))

        table = Table(
            title="Message History",
            title_style="bold",
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim", no_wrap=True)
        table.add_column("Role", style="green", no_wrap=True)
        table.add_column("Content", overflow="fold")

        for i, (role, content) in enumerate(rows):
            # Show one marker line per checkpoint, before the item it
            # precedes, numbered by its order in the checkpoint list.
            for ordinal in markers.get(i, []):
                table.add_row("", f"◉ checkpoint {ordinal}", "", style="bold yellow")

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
