"""
Tests for shell command autocompletion.

The interactive shell wires a :class:`janito.shell.completer.CommandCompleter`
into its ``prompt_toolkit`` session so that typing a partial slash command
(e.g. ``/t``) suggests the matching registered commands (e.g. ``/tools``).
These tests verify the completer's matching logic, its case-insensitivity,
that plain (non-command) input is left untouched, and that the completer is
correctly attached to the shell's session.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from janito.shell.completer import CommandCompleter


class _FakeCmd:
    """Minimal command handler exposing only a ``name`` (what the completer uses)."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name


def _completer(names):
    """Build a CommandCompleter backed by fake commands with the given names."""
    commands = [_FakeCmd(n) for n in names]
    return CommandCompleter(lambda: commands)


def _completions_for(completer, text):
    """Return the completion texts suggested for the given input."""
    doc = Document(text, cursor_position=len(text))
    return [c.text for c in completer.get_completions(doc, CompleteEvent())]


if pytest is not None:

    def test_completes_matching_prefix():
        completer = _completer(["/tools", "/help", "/history"])
        assert _completions_for(completer, "/t") == ["/tools"]

    def test_multiple_matches_sorted_alphabetically():
        completer = _completer(["/history", "/help"])
        assert _completions_for(completer, "/h") == ["/help", "/history"]

    def test_slash_alone_lists_every_command():
        completer = _completer(["/tools", "/ask", "/show_config"])
        assert _completions_for(completer, "/") == ["/ask", "/show_config", "/tools"]

    def test_exact_match_is_offered():
        completer = _completer(["/exit"])
        assert _completions_for(completer, "/exit") == ["/exit"]

    def test_no_match_yields_nothing():
        completer = _completer(["/tools", "/help"])
        assert _completions_for(completer, "/zzz") == []

    def test_non_command_input_is_untouched():
        completer = _completer(["/tools"])
        assert _completions_for(completer, "hello") == []

    def test_empty_input_yields_nothing():
        completer = _completer(["/tools"])
        assert _completions_for(completer, "") == []

    def test_case_insensitive_matching():
        completer = _completer(["/tools"])
        assert _completions_for(completer, "/T") == ["/tools"]
        assert _completions_for(completer, "/TOOL") == ["/tools"]

    def test_completion_replaces_only_command_token():
        completer = _completer(["/tools"])
        doc = Document("/t", cursor_position=2)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert len(completions) == 1
        # start_position is the number of chars to remove before inserting.
        assert completions[0].start_position == -len("/t")
        # display_meta is stored as formatted text; its content is "command".
        meta = completions[0].display_meta
        assert "command" in "".join(part[1] for part in meta)

    def test_completer_uses_registered_commands():
        # The real registered command set should include the well-known commands.
        from janito.shell.cmds import get_registered_commands

        completer = CommandCompleter(get_registered_commands)
        names = _completions_for(completer, "/")
        assert "/help" in names
        assert "/tools" in names
        assert "/exit" in names

    def test_session_has_completer_and_complete_while_typing():
        # Building an InteractiveShell wires the completer into its session.
        from janito.shell import InteractiveShell

        shell = InteractiveShell(model="test-model", no_history=True)
        assert isinstance(shell.session.completer, CommandCompleter)
        assert shell.session.complete_while_typing is True

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
