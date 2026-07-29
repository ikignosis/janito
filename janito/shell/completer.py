"""
Command autocompletion for the interactive shell.

Provides a :class:`prompt_toolkit` ``Completer`` that suggests registered
slash commands (e.g. ``/tools``, ``/help``) as the user types. Suggestions
only appear once the current token starts with a ``/``, so regular chat
input is left untouched.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

if TYPE_CHECKING:
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from .cmds import CmdHandler


class CommandCompleter(Completer):
    """Autocomplete registered shell commands that start with ``/``.

    The completer inspects the word currently being typed. If that word
    starts with ``/`` (for example ``/t``), every registered command whose
    name starts with the same prefix is offered as a completion, sorted
    alphabetically. Words that do not start with ``/`` yield no suggestions,
    keeping plain chat input free of command noise.

    Args:
        commands: A zero-argument callable returning the current list of
            registered command handlers. Passing a callable (rather than a
            fixed list) keeps the completer in sync with commands registered
            after the completer is created.
    """

    def __init__(self, commands: Callable[[], list["CmdHandler"]]) -> None:
        self._commands = commands

    def get_completions(self, document: "Document", complete_event: "CompleteEvent"):
        """Yield completions for the command token before the cursor."""
        # Use WORD (vim-style) tokenisation so the leading ``/`` is kept as
        # part of the word, giving us the full command prefix (``/t``).
        word = document.get_word_before_cursor(WORD=True)

        # Only complete when the current token looks like a command.
        if not word.startswith("/"):
            return

        prefix = word
        for name in self._matching_command_names(prefix):
            yield Completion(
                name,
                start_position=-len(prefix),
                display=name,
                display_meta="command",
            )

    def _matching_command_names(self, prefix: str) -> list[str]:
        """Return sorted command names that start with ``prefix`` (case-insensitive)."""
        lowered = prefix.lower()
        names = [
            cmd.name for cmd in self._commands() if cmd.name.lower().startswith(lowered)
        ]
        return sorted(names)
