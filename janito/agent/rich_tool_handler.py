from janito.agent.tool_registry import register_tool, handle_tool_call, get_tool_schemas
from rich.console import Console
console = Console()

class MessageHandler:
    """
    Unified message handler for all output (tool, assistant, system) using Rich for styled output.
    """
    def __init__(self):
        self.console = console

    def handle_message(self, msg, msg_type=None):
        """
        Handles either a dict (with 'type' and 'message') or a plain string.
        If dict: uses type/message. If str: uses msg_type or defaults to 'info'.
        """
        from rich.markdown import Markdown
        if isinstance(msg, dict):
            msg_type = msg.get("type", "info")
            message = msg.get("message", "")
            if msg_type == "content":
                self.console.print(Markdown(message))
            elif msg_type == "info":
                self.console.print(message, style="cyan", end="")
            elif msg_type == "success":
                self.console.print(message, style="bold green", end="\n")
            elif msg_type == "error":
                self.console.print(message, style="bold red", end="\n")
            else:
                raise NotImplementedError(f"Unsupported message type: {msg_type}")
        else:
            # Print plain strings as markdown/markup
            self.console.print(Markdown(str(msg)))

