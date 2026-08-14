"""
Prompt-toolkit session setup for the interactive shell.

Extracted from :mod:`janito.shell.interactive` so the shell module stays
focused on the conversation loop, input dispatch and command handling.
"""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.styles import Style

from .completer import CommandCompleter

# History file path
HISTORY_FILE = Path.cwd() / ".janito" / "history.log"


class _SessionMixin:
    """Mixin providing prompt_toolkit session and history management."""

    def _get_bottom_toolbar(self) -> list:
        """Get the bottom toolbar content."""
        tokens = []

        # Model info
        tokens.append(("class:model", f" model: {self.model} "))

        # Provider info (if available)
        try:
            from janito.general_config import get_active_provider

            provider = self.provider or get_active_provider()
            if provider:
                tokens.append(("", " \u2502 "))
                tokens.append(("class:provider", f" provider: {provider} "))
        except Exception:
            pass

        # Keyboard shortcuts
        tokens.append(("", " \u2502 "))
        tokens.append(("class:key-label", "[F2] restart "))
        tokens.append(("class:key-label", "[F12] do-it "))
        tokens.append(("class:key-label", "[/exit] end "))
        tokens.append(("class:key-label", "[!cmd] shell "))

        # Multiline mode indicator
        if getattr(self, "multiline_mode", False):
            tokens.append(("class:key-toggle-on", "[multi] "))

        return tokens

    def _create_session(self, multiline: bool = False) -> PromptSession:
        """Create and configure the prompt_toolkit session."""
        kb = KeyBindings()

        @kb.add("f2")
        def restart_chat(event: KeyPressEvent) -> None:
            """Handle F2 key to restart conversation."""
            self.restart_requested = True
            event.app.exit(result=None)

        @kb.add("f12")
        def do_it_action(event: KeyPressEvent) -> None:
            """Handle F12 key to trigger 'Do It' auto-execution."""
            self.do_it_requested = True
            event.app.exit(result="Do It")

        # Style for the chat shell
        chat_shell_style = Style.from_dict(
            {
                "prompt": "bg:#2323af #ffffff bold",
                "": "bg:#005fdd #ffffff",  # blue background for input area
                "bottom-toolbar": "fg:#232323 bg:#f0f0f0",
                "key-label": "bg:#ff9500 fg:#232323 bold",
                "provider": "fg:#117fbf",
                "model": "fg:#1f5fa9",
                "role": "fg:#e87c32 bold",
                "msg_count": "fg:#5454dd",
                "session_id": "fg:#704ab9",
                "tokens_total": "fg:#a022c7",
                "tokens_in": "fg:#00af5f",
                "tokens_out": "fg:#01814a",
                "max-tokens": "fg:#888888",
                "key-toggle-on": "bg:#ffd700 fg:#232323 bold",
                "key-toggle-off": "bg:#444444 fg:#ffffff bold",
                "cmd-label": "bg:#ff9500 fg:#232323 bold",
            }
        )

        # Set up history based on no_history flag
        if self.no_history:
            # In-memory only - don't persist to file
            history = InMemoryHistory()
        else:
            # Persist to file in current directory
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(HISTORY_FILE))

        return PromptSession(
            history=history,
            key_bindings=kb,
            style=chat_shell_style,
            bottom_toolbar=lambda: self._get_bottom_toolbar(),
            multiline=multiline,
            completer=CommandCompleter(lambda: self.commands),
            complete_while_typing=True,
        )

    @staticmethod
    def get_history_file_path() -> Path:
        """Get the path to the history log file.

        Returns:
            Path: Path to ~/.janito/history.log
        """
        return HISTORY_FILE

    @staticmethod
    def clear_input_history() -> None:
        """Clear the input history log file."""
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
            print(f"Input history cleared from: {HISTORY_FILE}")
        else:
            print("No input history file found.")
