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
        # Check trust config: suppress all output except 'content' if enabled
        trust = runtime_config.get("trust")
        if trust is None:
            trust = unified_config.get("trust", False)

        from rich.markdown import Markdown

        if not isinstance(msg, dict):
            raise TypeError(
                f"RichMessageHandler.handle_message expects a dict with 'type' and 'message', got {type(msg)}: {msg!r}"
            )

        msg_type = msg.get("type", "info")
        message = msg.get("message", "")

        if trust and msg_type != "content":
            return  # Suppress all except content
        if msg_type == "content":
            self.console.print(Markdown(message))
        elif msg_type == "info":
            self.console.print(f"  {message}", style="cyan", end="")
        elif msg_type == "success":
            self.console.print(message, style="bold green", end="\n")
        elif msg_type == "error":
            self.console.print(message, style="bold red", end="\n")
        elif msg_type == "progress":
            self._handle_progress(message)
        elif msg_type == "warning":
            self.console.print(message, style="bold yellow", end="\n")
        elif msg_type == "stdout":
            from rich.text import Text

            self.console.print(
                Text(message, style="on #003300", no_wrap=True, overflow=None),
                end="",
            )
        elif msg_type == "stderr":
            from rich.text import Text

            self.console.print(
                Text(message, style="on #330000", no_wrap=True, overflow=None),
                end="",
            )
        else:
            # Ignore unsupported message types silently
            return
