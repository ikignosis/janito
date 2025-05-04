from rich.console import Console
from janito.agent.runtime_config import runtime_config, unified_config
from janito.agent.message_handler_protocol import MessageHandlerProtocol

console = Console()


class RichMessageHandler(MessageHandlerProtocol):
    """
    Unified message handler for all output (tool, agent, system) using Rich for styled output.
    """

    def __init__(self):
        self.console = console

    def handle_message(self, msg, msg_type=None):
        """
        Handles a dict with 'type' and 'message'.
        All messages must be dicts. Raises if not.
        """
        trust = runtime_config.get("trust")
        if trust is None:
            trust = unified_config.get("trust", False)

        if not isinstance(msg, dict):
            raise TypeError(
                f"RichMessageHandler.handle_message expects a dict with 'type' and 'message', got {type(msg)}: {msg!r}"
            )

        msg_type = msg.get("type", "info")
        message = msg.get("message", "")

        if trust and msg_type != "content":
            return  # Suppress all except content

        handler_map = {
            "content": self._handle_content,
            "info": self._handle_info,
            "success": self._handle_success,
            "error": self._handle_error,
            "progress": self._handle_progress,
            "warning": self._handle_warning,
            "stdout": self._handle_stdout,
            "stderr": self._handle_stderr,
        }

        handler = handler_map.get(msg_type)
        if handler:
            handler(msg, message)
        # Ignore unsupported message types silently

    def _handle_content(self, msg, message):
        from rich.markdown import Markdown

        self.console.print(Markdown(message))

    def _handle_info(self, msg, message):
        action_type = msg.get("action_type", None)
        style = "cyan"  # default
        action_type_name = action_type.name if action_type else None
        if action_type_name == "READ":
            style = "cyan"
        elif action_type_name == "WRITE":
            style = "bright_magenta"
        elif action_type_name == "EXECUTE":
            style = "yellow"
        self.console.print(f"  {message}", style=style, end="")

    def _handle_success(self, msg, message):
        self.console.print(message, style="bold green", end="\n")

    def _handle_error(self, msg, message):
        self.console.print(message, style="bold red", end="\n")

    def _handle_progress(self, msg, message=None):
        # Existing logic for progress messages (if any)
        # Placeholder: implement as needed
        pass

    def _handle_warning(self, msg, message):
        self.console.print(message, style="bold yellow", end="\n")

    def _handle_stdout(self, msg, message):
        from rich.text import Text

        self.console.print(
            Text(message, style="on #003300", no_wrap=True, overflow=None),
            end="",
        )

    def _handle_stderr(self, msg, message):
        from rich.text import Text

        self.console.print(
            Text(message, style="on #330000", no_wrap=True, overflow=None),
            end="",
        )
