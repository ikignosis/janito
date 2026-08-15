"""
Command autocompletion for the interactive shell.

Provides a :class:`prompt_toolkit` ``Completer`` that suggests registered
slash commands (e.g. ``/tools``, ``/help``) as the user types. Suggestions
only appear once the current token starts with a ``/`` **and** that token
is the first one on the line, so regular chat input is left untouched.

Commands that take an argument can register an *argument completer*: a
callable that receives the current word and returns the candidate argument
values. When the line so far matches ``/cmd <word>`` the candidates are
offered instead, e.g. ``/provider`` suggests the available provider names.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

if TYPE_CHECKING:
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from .cmds import CmdHandler


class CommandCompleter(Completer):
    """Autocomplete registered shell commands that start with ``/``.

    The completer inspects the word currently being typed. If that word
    starts with ``/`` (for example ``/t``) **and** is the first token on
    the line, every registered command whose name starts with the same
    prefix is offered as a completion, sorted alphabetically. A ``/`` that
    appears in the middle of a prompt is treated as regular chat text and
    yields no suggestions, keeping plain chat input free of command noise.

    When a registered command declares an argument completer (via
    ``arg_completers``), typing ``/cmd <word>`` offers that command's
    candidate argument values instead of command names.

    Args:
        commands: A zero-argument callable returning the current list of
            registered command handlers. Passing a callable (rather than a
            fixed list) keeps the completer in sync with commands registered
            after the completer is created.
        arg_completers: Optional mapping from command name (e.g. ``"/provider"``)
            to a callable that receives the current word and returns the
            candidate argument values (e.g. the available provider names).
    """

    def __init__(
        self,
        commands: Callable[[], list["CmdHandler"]],
        arg_completers: dict[str, Callable[[str], Iterable[str]]] | None = None,
    ) -> None:
        self._commands = commands
        self._arg_completers = arg_completers or {}

    def get_completions(self, document: "Document", complete_event: "CompleteEvent"):
        """Yield completions for the command token before the cursor."""
        # Use WORD (vim-style) tokenisation so the leading ``/`` is kept as
        # part of the word, giving us the full command prefix (``/t``).
        word = document.get_word_before_cursor(WORD=True)

        # Only complete when the current token looks like a command.
        if word.startswith("/"):
            # Only trigger when the ``/`` token is the first one on the line; a
            # slash anywhere else is regular chat text, not a command.
            line_before = document.current_line_before_cursor
            before_word = line_before[: -len(word)] if word else line_before
            if not before_word.strip():
                prefix = word
                for name in self._matching_command_names(prefix):
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                        display=name,
                        display_meta="command",
                    )
                return

        # Argument completion: for a line that matches ``/cmd <first-word>``
        # ask the command's arg completer for candidate values. Only the first
        # argument is completed (a second space means the user moved on).
        line_before = document.current_line_before_cursor.lstrip()
        for cmd_name, arg_completer in self._arg_completers.items():
            cmd_prefix = f"{cmd_name} "
            if line_before.lower().startswith(cmd_prefix.lower()):
                rest = line_before[len(cmd_prefix) :]
                if " " not in rest:
                    for name in sorted(arg_completer(word), key=str.lower):
                        yield Completion(
                            name,
                            start_position=-len(word),
                            display=name,
                            display_meta="argument",
                        )
                return

    def _matching_command_names(self, prefix: str) -> list[str]:
        """Return sorted command names that start with ``prefix`` (case-insensitive)."""
        lowered = prefix.lower()
        names = [
            cmd.name for cmd in self._commands() if cmd.name.lower().startswith(lowered)
        ]
        return sorted(names)
