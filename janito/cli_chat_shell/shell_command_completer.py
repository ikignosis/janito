from prompt_toolkit.completion import Completer, Completion


class ShellCommandCompleter(Completer):
    def __init__(self):
        # Import here to avoid circular import at module level
        from janito.cli_chat_shell.commands import COMMAND_HANDLERS

        # Only commands starting with '/'
        self.commands = sorted(
            [cmd for cmd in COMMAND_HANDLERS.keys() if cmd.startswith("/")]
        )

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            prefix = text[1:]
            for cmd in self.commands:
                if cmd[1:].startswith(prefix):
                    yield Completion(cmd, start_position=-(len(prefix) + 1))
