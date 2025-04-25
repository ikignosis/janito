from rich.console import Console
from janito.agent.runtime_config import runtime_config, unified_config
from janito.agent.message_handler_protocol import MessageHandlerProtocol
import re
import os

console = Console()


def _replace_filenames_with_links(markdown_text):
    """
    Scan markdown for filename-like patterns and replace with Markdown links to localhost if file exists and termweb_port is set.
    """
    port = runtime_config.get("termweb_port")
    if not port:
        return markdown_text  # No transformation if no port

    # Pattern: words with dots and/or slashes, e.g. foo.py, path/to/file.md
    # Avoid matching URLs or already-linked text
    pattern = r"(?<!\w)([\w./\\-]+\.[\w]+)(?![\w/])"

    def replacer(match):
        filename = match.group(1)
        if filename.startswith("http://") or filename.startswith("https://"):
            return filename
        # Normalize path
        path = os.path.normpath(filename)
        if os.path.exists(path):
            abs_path = os.path.abspath(path)
            try:
                rel_path = os.path.relpath(abs_path, os.getcwd())
            except ValueError:
                rel_path = abs_path  # fallback if relpath fails
            url = f"http://localhost:{port}/?path={abs_path}"
            return f"[{rel_path}]({url})"
        return filename

    return re.sub(pattern, replacer, markdown_text)


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

        def _remove_surrogates(text):
            return "".join(c for c in text if not 0xD800 <= ord(c) <= 0xDFFF)

        safe_message = (
            _remove_surrogates(message) if isinstance(message, str) else message
        )

        if trust and msg_type != "content":
            return  # Suppress all except content
        if msg_type == "content":
            # --- New logic: replace filenames with Markdown links ---
            if isinstance(safe_message, str):
                safe_message = _replace_filenames_with_links(safe_message)
            self.console.print(Markdown(safe_message))
        elif msg_type == "info":
            self.console.print(safe_message, style="cyan", end="")
        elif msg_type == "success":
            self.console.print(safe_message, style="bold green", end="\n")
        elif msg_type == "error":
            self.console.print(safe_message, style="bold red", end="\n")
        elif msg_type == "progress":
            self._handle_progress(safe_message)
        elif msg_type == "warning":
            self.console.print(safe_message, style="bold yellow", end="\n")
        elif msg_type == "stdout":
            from rich.text import Text

            self.console.print(
                Text(safe_message, style="on #003300", no_wrap=True, overflow=None),
                end="",
            )
        elif msg_type == "stderr":
            from rich.text import Text

            self.console.print(
                Text(safe_message, style="on #330000", no_wrap=True, overflow=None),
                end="",
            )
        else:
            # Ignore unsupported message types silently
            return
