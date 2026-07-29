"""
/changes command handler - displays the tool executions logged for the current prompt.

Reads the ``./.janito/changes.jsonl`` file written by
:mod:`janito.tooling.changes` (populated for every successful tool call whose
first argument is ``filepath``) and renders each execution in a friendly,
human-readable format:

* ``CreateFile`` - the written ``content`` is shown with rich syntax
  highlighting (language guessed from the file path).
* ``ReplaceTextInFile`` - a unified diff between ``old_str`` and ``new_str``
  is generated and shown, syntax-highlighted.
* Any other tool - its parameters are shown as pretty-printed JSON.
"""

from __future__ import annotations

from .base import CmdHandler
from .registry import register_command


class ChangesCmdHandler(CmdHandler):
    """Command handler for the /changes command."""

    @property
    def name(self) -> str:
        return "/changes"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /changes command."""
        if user_input.strip().lower() == self.name.lower():
            self._print_changes()
            return True
        return False

    def _print_changes(self) -> None:
        """Print the recorded changes (or a friendly message)."""
        from janito.tooling.changes import render_changes

        render_changes()


# Register this handler
_handler = ChangesCmdHandler()
register_command(_handler)
