"""
Interactive shell implementation using prompt_toolkit.
"""

import contextlib
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from prompt_toolkit.formatted_text import HTML
from rich.console import Console

from ..openai_client import RequestCancelled
from .session import _SessionMixin

_rich_console = Console(markup=False)

if TYPE_CHECKING:
    from .cmds import CmdHandler


class InteractiveShell(_SessionMixin):
    """Interactive shell for chat sessions using prompt_toolkit."""

    def __init__(
        self,
        model: str,
        commands: list["CmdHandler"] | None = None,
        no_history: bool = False,
        provider: str | None = None,
        thinking: bool = False,
        api_type: str | None = None,
    ):
        """
        Initialize the interactive shell.

        Args:
            model: The model name to display in the prompt
            commands: List of command handlers (auto-loaded if not provided)
            no_history: If True, use in-memory history only (no file persistence)
            provider: The provider name in effect for this session (e.g. from
                ``--provider``, updated by ``/provider``). When set, the
                status bar reports it; otherwise it falls back to the
                configured default provider.
            thinking: If True, enable thinking mode for the session.
            api_type: The API type passed via ``--api-type`` (e.g. ``Gemini``,
                ``Responses``, ``Completions``). ``None`` when the CLI flag
                was not given, in which case the effective API type resolves
                from the provider/model configuration (see
                :func:`janito.general_config.resolve_api_type`). Surfaced by
                ``/status`` so it reports the API type actually in use.
        """
        self.model = model
        self.provider = provider
        self.thinking = thinking
        self.api_type = api_type
        # Set by /model for the current session: the explicit model override
        # that the send factory (re)built by /provider and /model consults so
        # the runtime model matches the displayed one.  Cleared when /provider
        # switches to another provider (the new provider resolves its own
        # model).
        self.model_override = None
        self.no_history = no_history
        # Conversation messages (role/content dicts) passed to the AI as
        # context
        self.messages_history: list[dict[str, Any]] = []
        # Index into messages_history marking the last known-good state;
        # /rewind and error recovery truncate back to here
        self.history_checkpoint: int = 0
        # Server-side conversation handle for the Responses API: the id of the
        # last response, passed as `previous_response_id` on the next turn.
        # None in Completions mode (where history lives in messages_history),
        # when no Responses conversation has started yet, and for stateless
        # Responses providers (which never chain with an id).
        self.previous_response_id: str | None = None
        # Client-side Responses input items. For stateless Responses providers
        # (e.g. DeepSeek, whose /responses endpoint keeps no server state):
        # the full conversation, re-sent on every request via `previous_items`.
        # For server-side Responses providers (e.g. OpenAI): the pending user
        # messages of Enter-cancelled turns, re-sent as input items chained
        # from the last completed response id (see previous_response_id) and
        # cleared again once a turn completes. None in Completions mode and
        # for server-side Responses providers with no pending messages.
        self.conversation_items: list[dict[str, Any]] | None = None
        # Index into conversation_items marking the last known-good state;
        # /rewind truncates back to here.
        self.conversation_checkpoint: int = 0
        # Chain of completed server-side Responses response ids, in turn
        # order. Every successful turn of a server-side Responses provider
        # (e.g. OpenAI) appends its final response id; /rewind truncates
        # back to the checkpoint and re-points previous_response_id at the
        # response that preceded the rolled-back exchange, so the next turn
        # continues from there instead of resetting the whole server-side
        # conversation. Empty in Completions mode and for stateless
        # Responses providers (which never chain with an id).
        self.response_chain: list[str] = []
        # Index into response_chain marking the last known-good state;
        # /rewind truncates back to here.
        self.response_checkpoint: int = 0
        # Display-only mirror of completed server-side Responses turns (e.g.
        # OpenAI), kept client-side purely so /history can render the
        # conversation: the real history lives on the server (chained via
        # previous_response_id) and is never fetched back. Same Responses
        # input-item format as conversation_items (message / function_call /
        # function_call_output); the system prompt stays in messages_history.
        # Empty in Completions mode and for stateless Responses providers
        # (which mirror through conversation_items instead).
        self.mirrored_history: list[dict[str, Any]] = []
        # Index into mirrored_history marking the last known-good state;
        # /rewind truncates back to here.
        self.mirrored_checkpoint: int = 0
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

    def initialize_history(self, system_prompt: str | None = None) -> None:
        """
        Initialize the messages history.

        Args:
            system_prompt: Optional system prompt to prepend
        """
        self._system_prompt = system_prompt  # stored so it can be restored on F2/clear without re-reading config
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
        self.response_chain = []
        self.response_checkpoint = 0
        # A fresh conversation also clears the /history display mirror of
        # completed server-side turns.
        self.mirrored_history = []
        self.mirrored_checkpoint = 0

    def get_system_prompt(self) -> str | None:
        """Get the current system prompt."""
        return self._system_prompt

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
        # Clear screen before printing the message
        os.system("cls" if os.name == "nt" else "clear")
        self._reset_conversation(
            "[Keybinding F2] Conversation history cleared. Starting fresh conversation."
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

    @contextlib.contextmanager
    def _cooked_terminal(self) -> Iterator[None]:
        """Temporarily restore the terminal to cooked mode (POSIX only).

        prompt_toolkit drives the terminal in raw mode while the prompt app
        is running; by the time a ``!cmd`` is dispatched the terminal is
        already back to cooked mode, but forcing it here guarantees that
        full-screen programs (vim, less, ...) start from a sane state and
        that a command that crashes mid-way doesn't leave the shell with a
        raw / no-echo terminal. On Windows and when stdin is not a TTY
        (e.g. tests) there is nothing to restore.
        """
        if os.name == "nt" or not sys.stdin.isatty():
            yield
            return

        import termios

        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        cooked = termios.tcgetattr(fd)
        cooked[3] |= termios.ICANON | termios.ECHO
        try:
            termios.tcsetattr(fd, termios.TCSANOW, cooked)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, saved)

    def _run_shell_command(self, user_input: str) -> None:
        """Execute a ``!cmd`` shell command.

        The command inherits the real terminal (stdin/stdout/stderr are not
        captured) so interactive, full-screen programs such as vim or less
        work; plain commands print directly to the terminal. While the
        command runs, SIGINT is ignored in the parent (the child keeps the
        default handler unless it installs its own, e.g. vim) so Ctrl+C is
        handled by the running program instead of aborting the wait and
        leaving it orphaned. There is no timeout: interactive commands can
        legitimately run for as long as the user needs, and a command that
        hangs can be interrupted the usual way.
        """
        cmd = user_input[1:].strip()
        if not cmd:
            return
        print(f"[Shell] Executing: {cmd}")
        try:
            with self._cooked_terminal():
                # Mirror os.system()'s SIGINT handling: block it in the
                # parent while the child runs so the child (which inherits
                # the default disposition) can deal with Ctrl+C itself.
                old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
                try:
                    result = subprocess.run(cmd, shell=True)
                finally:
                    signal.signal(signal.SIGINT, old_handler)
            print(f"[Shell] Exit code: {result.returncode}")
        except KeyboardInterrupt:
            print("\n[Shell] Command interrupted", file=sys.stderr)
        except Exception as e:
            print(f"[Shell] Error: {e}", file=sys.stderr)

    def _dispatch_input(self, user_input: str) -> bool:
        """Handle clear/command/unknown/shell input; True when consumed."""
        if user_input.lower() == "clear":
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

    def _send_prompt(
        self, user_input: str, tools: list[dict[str, Any]] | None = None
    ) -> None:
        """Send a prompt to the AI and update the conversation state.

        Args:
            user_input: The user's prompt text.
            tools: Optional explicit tool schemas to offer the model. When
                ``None`` (default) the session default applies (all tools, or
                none when ``no_tools`` is set); pass a list to restrict the
                model to a subset of tools (e.g. the read-only tools used by
                ``/read``).
        """
        if tools is None:
            tools_to_use = [] if self.no_tools else None
        else:
            tools_to_use = tools
        # Save checkpoint so we can rollback history on cancel/error
        self.history_checkpoint = len(self.messages_history)
        self.conversation_checkpoint = (
            len(self.conversation_items) if self.conversation_items else 0
        )
        self.response_checkpoint = len(self.response_chain)
        self.mirrored_checkpoint = len(self.mirrored_history)
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
            # Responses API mode keeps the conversation state the provider
            # uses; Completions mode returns plain text and updates
            # previous_messages (self.messages_history) in place, so nothing
            # else is needed there.
            if hasattr(result, "input_items"):
                self._record_responses_result(result)
            # On success, keep the checkpoint where it is (before this turn)
            # so /rewind can undo the last exchange. The next turn will
            # update it before its own send_prompt call.
        except RequestCancelled as e:
            # Enter was pressed while waiting for the API: interrupt the
            # request but keep the conversation intact so the next turn still
            # knows the user's message (no rollback, unlike Ctrl+C above).
            # The client never chains the next turn from the aborted request:
            # server-side Responses providers (e.g. OpenAI) discard the
            # response of an interrupted stream, so its id cannot be used as
            # previous_response_id. Instead the client hands back the user's
            # messages as input items; the shell keeps the last completed
            # response id (previous_response_id) and re-sends those items
            # chained from it on the next turn.
            items = getattr(e, "conversation_items", None)
            if items is not None:
                # Server-side Responses: the pending cancelled messages.
                # Stateless Responses (e.g. DeepSeek): the full client-side
                # items, which already include the cancelled message (this
                # also covers a fresh conversation, where the shell had no
                # items yet). Either way, store them so the next turn
                # re-sends them.
                self.conversation_items = items
            elif self.conversation_items is not None:
                # Fallback for stateless flows where the exception carries no
                # items (e.g. the abort happened before the client built
                # them): persist the cancelled message so the next turn
                # includes it.
                self.conversation_items.append(
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_input}],
                    }
                )
            print(
                "Request cancelled (Enter). The prompt stays in the conversation history."
            )
        except KeyboardInterrupt:
            # Rollback any messages appended during this prompt
            del self.messages_history[self.history_checkpoint :]
            print(
                "Request interrupted, previous prompt/answer removed from the conversation history."
            )
        except Exception as e:
            # Rollback on any other unexpected error as well
            del self.messages_history[self.history_checkpoint :]
            print(f"Error: {e}")
        # Note: send_prompt_func already appends user and assistant messages
        # to previous_messages (which is self.messages_history), so we don't
        # need to append them here.

    def _record_responses_result(self, result: Any) -> None:
        """Record the conversation state a Responses turn returns.

        Server-side providers (e.g. OpenAI) keep the history on the server:
        remember the returned response id to chain the next turn, and mirror
        the completed turn client-side (display-only) so /history can render
        the conversation. Stateless providers (e.g. DeepSeek) return the full
        conversation as input items (re-sent on the next turn); never chain
        with an id for them, and no mirror is kept (conversation_items is the
        mirror).
        """
        self.conversation_items = result.input_items
        if result.input_items is None:
            self.previous_response_id = result.response_id
            # Server-side Responses: remember this turn's final response id
            # in the chain so /rewind can undo the exchange by chaining the
            # next turn (previous_response_id) from the response that
            # preceded it, instead of resetting the whole server conversation.
            if result.response_id:
                self.response_chain.append(result.response_id)
            # Mirror the completed turn client-side (display-only) so
            # /history can render the conversation: the real history lives on
            # the server and is never fetched back. Pending Enter-cancelled
            # messages are not part of a completed turn and keep showing via
            # conversation_items instead.
            turn_items = getattr(result, "turn_items", None)
            if turn_items:
                self.mirrored_history.extend(turn_items)
        else:
            self.previous_response_id = None

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

            # Handle clear text, registered commands, unknown commands and
            # !cmd shell execution.
            if self._dispatch_input(user_input):
                # Check if exit was requested via a command
                if self.exit_requested:
                    break
                continue

            if user_input.strip():
                self._send_prompt(user_input)

        print("\nChat session ended.")
