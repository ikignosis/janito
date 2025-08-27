from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from janito.cli.console import shared_console
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler


class MultiShellHandler(ShellCmdHandler):
    help_text = "Prompt for multi-line input and display the result. Usage: /multi"

    def run(self):
        shared_console.print(
            "[bold blue]Entering multi-line input mode. Press Esc+Enter or Ctrl+D to submit, Ctrl+C to cancel.[/bold blue]"
        )
        # Prompt for multi-line input
        bindings = KeyBindings()
        submitted = {"value": None}

        @bindings.add("escape", "enter")
        def _(event):
            buffer = event.app.current_buffer
            submitted["value"] = buffer.text
            event.app.exit(result=buffer.text)

        # Support single ESC to cancel/interrupt (like Ctrl+C)
        @bindings.add("escape")
        def _(event):
            raise KeyboardInterrupt

        # Support Ctrl+D
        @bindings.add("c-d")
        def _(event):
            buffer = event.app.current_buffer
            submitted["value"] = buffer.text
            event.app.exit(result=buffer.text)

        try:
            user_input = prompt(
                "Multi-line > ",
                multiline=True,
                key_bindings=bindings,
            )
        except (EOFError, KeyboardInterrupt):
            shared_console.print("[red]Multi-line input cancelled.[/red]")
            return

        # Save input to history if available
        user_input_history = getattr(self.shell_state, "user_input_history", None)
        if user_input_history is not None:
            user_input_history.append(user_input)
        # Store input for main chat loop to consume as if just entered by the user
        self.shell_state.injected_input = user_input
        shared_console.print(
            "[green]Multi-line input will be sent as your next chat prompt.[/green]"
        )
