"""
Interactive shell implementation using prompt_toolkit.
"""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.styles import Style
from rich.console import Console

from ..openai_client import RequestCancelled
from .completer import CommandCompleter

_rich_console = Console(markup=False)

if TYPE_CHECKING:
    from .cmds import CmdHandler


# History file path
HISTORY_FILE = Path.cwd() / ".janito" / "history.log"


class InteractiveShell:
    """Interactive shell for chat sessions using prompt_toolkit."""

    def __init__(
        self,
        model: str,
        commands: list["CmdHandler"] | None = None,
        no_history: bool = False,
        provider: str | None = None,
    ):
        """
        Initialize the interactive shell.

        Args:
            model: The model name to display in the prompt
            commands: List of command handlers (auto-loaded if not provided)
            no_history: If True, use in-memory history only (no file persistence)
            provider: The provider name in effect for this session (e.g. from
                ``--provider``). When set, the status bar reports it; otherwise
                it falls back to the configured default provider.
        """
        self.model = model
        self.provider = provider
        self.no_history = no_history
        # Conversation messages (role/content dicts) passed to the AI as
        # context
        self.messages_history: list[dict[str, Any]] = []
        # Index into messages_history marking the last known-good state;
        # /rollback and error recovery truncate back to here
        self.history_checkpoint: int = 0
        # Server-side conversation handle for the Responses API: the id of the
        # last response, passed as `previous_response_id` on the next turn.
        # None in Completions mode (where history lives in messages_history),
        # when no Responses conversation has started yet, and for stateless
        # Responses providers (which never chain with an id).
        self.previous_response_id: str | None = None
        # Client-side Responses input items for stateless Responses providers
        # (e.g. DeepSeek, whose /responses endpoint keeps no server state):
        # the full conversation, re-sent on every request via `previous_items`.
        # None in Completions mode and for server-side Responses providers
        # (which keep the history on the server behind previous_response_id).
        self.conversation_items: list[dict[str, Any]] | None = None
        # Index into conversation_items marking the last known-good state;
        # /rollback truncates back to here.
        self.conversation_checkpoint: int = 0
        # Set True by the F2 key binding; signals the run loop to clear
        # history and start a fresh conversation
        self.restart_requested = False
        # Set True by the F12 key binding; signals the run loop to
        # auto-send a "Do It" prompt
        self.do_it_requested = False
        # Set True by the /exit command handler; signals the run loop to
        # break and end the session
        self.exit_requested = False
        # Set by /multi for the next prompt only; automatically resets
        # after a multiline input is submitted
        self.multiline_mode = False

        # Auto-load registered commands if not provided
        if commands is None:
            from .cmds import get_registered_commands

            self.commands = get_registered_commands()
        else:
            self.commands = commands

        # Create session after commands are loaded
        self.session = self._create_session()

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
                tokens.append(("", " │ "))
                tokens.append(("class:provider", f" provider: {provider} "))
        except Exception:
            pass

        # Keyboard shortcuts
        tokens.append(("", " │ "))
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

    def initialize_history(self, system_prompt: str | None = None) -> None:
        """
        Initialize the messages history.

        Args:
            system_prompt: Optional system prompt to prepend
        """
        self._system_prompt = system_prompt  # stored so it can be restored on F2/restart without re-reading config
        if system_prompt:
            self.messages_history = [{"role": "system", "content": system_prompt}]
        else:
            self.messages_history = []
        # Checkpoint starts after the system prompt (if any)
        self.history_checkpoint = len(self.messages_history)
        # A fresh conversation also starts a fresh server-side conversation:
        # the next turn must not chain to the previous response id, and any
        # stateless client-side items history is dropped.
        self.previous_response_id = None
        self.conversation_items = None
        self.conversation_checkpoint = 0

    def get_system_prompt(self) -> str | None:
        """Get the current system prompt."""
        return self._system_prompt

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

    def _get_user_input(self) -> str | None:
        """Prompt for the next input line.

        Returns:
            The user's input, ``None`` to end the session (Ctrl+D, or a
            confirmed Ctrl+C quit), or ``""`` to continue without processing
            (Ctrl+C declined, or F2 restart requested).
        """
        # Use HTML formatting for prompt
        prompt_text = HTML(f'<style bg="#00008b">{self.model} # </style>')

        try:
            result = self.session.prompt(prompt_text, multiline=self.multiline_mode)
            if result is None and self.restart_requested:
                # F2 was pressed: the key binding exits the prompt app with a
                # ``None`` result, the same value the run loop uses to signal
                # "quit". Translate it into a "continue without processing"
                # signal here; the run loop handles the restart right after.
                return ""
            return result
        except KeyboardInterrupt:
            # User pressed Ctrl+C - ask to confirm quit
            try:
                confirm = self.session.prompt(
                    "\nDo you want to quit the conversation? (y/n): "
                )
                if confirm and confirm.lower().strip() in ["y", "yes"]:
                    return None  # User wants to quit
                return ""  # User doesn't want to quit, continue to next iteration
            except (KeyboardInterrupt, EOFError):
                # User pressed Ctrl+C or Ctrl+D again during confirmation
                return None  # Quit
        except EOFError:
            # User pressed Ctrl+D at main prompt
            return None

    def _handle_restart_request(self) -> bool:
        """Handle the F2 restart keybinding; True when the loop continues."""
        if not self.restart_requested:
            return False
        # Reset to a fresh conversation while preserving the system prompt
        # (matches startup behaviour). A plain .clear() would drop the
        # system prompt and leave an empty history.
        self.initialize_history(system_prompt=self._system_prompt)
        # Clear screen before printing the message
        os.system("cls" if os.name == "nt" else "clear")
        _rich_console.print(
            "[Keybinding F2] Conversation history cleared. Starting fresh conversation.",
            style="bold white on green",
        )
        return True

    def _reset_conversation(self, message: str) -> None:
        """Reset to a fresh conversation while preserving the system prompt."""
        self.initialize_history(system_prompt=self._system_prompt)
        _rich_console.print(message, style="bold white on green")

    def _handle_command(self, user_input: str) -> bool:
        """Dispatch to registered command handlers; True when handled."""
        for cmd_handler in self.commands:
            if cmd_handler.handle(self, user_input):
                return True
        return False

    def _is_unknown_command(self, user_input: str) -> bool:
        """Reject unrecognized slash commands; True when handled."""
        if user_input.strip().startswith("/"):
            cmd_name = user_input.strip().split()[0]
            print(f"Unknown command: {cmd_name}")
            print("Type /help to see available commands.")
            return True
        return False

    def _run_shell_command(self, user_input: str) -> None:
        """Execute a ``!cmd`` shell command."""
        import sys

        cmd = user_input[1:].strip()
        if not cmd:
            return
        print(f"[Shell] Executing: {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            print(f"[Shell] Exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            print(
                "[Shell] Command timed out after 60 seconds",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[Shell] Error: {e}", file=sys.stderr)

    def _dispatch_input(self, user_input: str) -> bool:
        """Handle restart/command/unknown/shell input; True when consumed."""
        if user_input.lower() == "restart":
            # Reset to a fresh conversation while preserving the system
            # prompt (matches startup behaviour). A plain .clear() would
            # drop the system prompt and leave an empty history.
            self._reset_conversation(
                "Conversation history cleared. Starting fresh conversation."
            )
            return True

        # Handle registered commands
        if self._handle_command(user_input):
            return True

        # Reject unrecognized slash commands instead of sending them to the LLM
        if self._is_unknown_command(user_input):
            return True

        # Handle !cmd for direct shell execution
        if user_input.startswith("!"):
            self._run_shell_command(user_input)
            return True

        return False

    def _send_prompt(self, user_input: str) -> None:
        """Send a prompt to the AI and update the conversation state."""
        tools_to_use = [] if self.no_tools else None
        # Save checkpoint so we can rollback history on cancel/error
        self.history_checkpoint = len(self.messages_history)
        self.conversation_checkpoint = (
            len(self.conversation_items) if self.conversation_items else 0
        )
        try:
            result = self.send_prompt_func(
                user_input,
                verbose=self.verbose,
                previous_messages=self.messages_history,
                previous_response_id=self.previous_response_id,
                previous_items=self.conversation_items,
                instructions=self.get_system_prompt(),
                tools=tools_to_use,
                thinking=self.thinking,
            )
            # Responses API mode: keep the conversation state the provider
            # uses. Server-side providers (e.g. OpenAI) keep the history on
            # the server, so remember the returned response id to chain the
            # next turn. Stateless providers (e.g. DeepSeek) return the full
            # conversation as input items, which are re-sent on the next turn;
            # never chain with an id for them. Completions mode returns plain
            # text and updates previous_messages (self.messages_history) in
            # place, so nothing else is needed here.
            if hasattr(result, "input_items"):
                self.conversation_items = result.input_items
                if result.input_items is None:
                    self.previous_response_id = result.response_id
                else:
                    self.previous_response_id = None
            # On success, keep the checkpoint where it is (before this turn)
            # so /rollback can undo the last exchange. The next turn will
            # update it before its own send_prompt call.
        except KeyboardInterrupt:
            # Rollback any messages appended during this prompt
            del self.messages_history[self.history_checkpoint :]
            print(
                "Request interrupted, previous prompt/answer removed from the conversation history."
            )
        except RequestCancelled:
            # Enter was pressed while waiting for the API: interrupt
            # the request but keep the user's message in the
            # conversation history (no rollback, unlike Ctrl+C above).
            print(
                "Request cancelled (Enter). The prompt stays in the conversation history."
            )
        except Exception as e:
            # Rollback on any other unexpected error as well
            del self.messages_history[self.history_checkpoint :]
            print(f"Error: {e}")
        # Note: send_prompt_func already appends user and assistant messages
        # to previous_messages (which is self.messages_history), so we don't
        # need to append them here.

    def run(
        self,
        send_prompt_func: Callable,
        verbose: bool = False,
        no_tools: bool = False,
        thinking: bool = False,
    ) -> None:
        """
        Run the interactive chat loop.

        Args:
            send_prompt_func: Function to call to send prompts to the AI
            verbose: Enable verbose output
            no_tools: If True, don't pass any tools to the AI
            thinking: If True, enable thinking mode
        """
        # Store references so command handlers (e.g. /ask) can use them
        self.send_prompt_func = send_prompt_func
        self.verbose = verbose
        self.no_tools = no_tools
        self.thinking = thinking

        while True:
            self.restart_requested = False
            self.do_it_requested = False
            self.exit_requested = False

            user_input = self._get_user_input()
            if user_input is None:
                break  # User quit

            # Reset multiline mode after input is received (single-use)
            if self.multiline_mode:
                self.multiline_mode = False
                self.session = self._create_session(multiline=False)

            # Check if F12 was pressed (Do It requested)
            if self.do_it_requested:
                print("\n[Keybinding F12] 'Do It' to continue existing plan...")
                user_input = "Do It"

            # Check if F2 was pressed (restart requested)
            if self._handle_restart_request():
                continue

            # Handle restart text, registered commands, unknown commands and
            # !cmd shell execution.
            if self._dispatch_input(user_input):
                # Check if exit was requested via a command
                if self.exit_requested:
                    break
                continue

            if user_input.strip():
                self._send_prompt(user_input)

        print("\nChat session ended.")
