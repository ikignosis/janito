from rich.console import Console
from rich.markdown import Markdown
from rich.pretty import Pretty
from rich.panel import Panel
from rich.text import Text
from janito.event_bus.handler import EventHandlerBase
import janito.driver_events as driver_events
from janito.report_events import ReportSubtype, ReportAction
from janito.event_bus.bus import event_bus
from janito.llm import message_parts
import janito.agent_events as agent_events


import sys


class RichTerminalReporter(EventHandlerBase):
    """
    Handles UI rendering for janito events using Rich.

    - For ResponseReceived events, iterates over the 'parts' field and displays each part appropriately:
        - TextMessagePart: rendered as Markdown (uses 'content' field)
        - Other MessageParts: displayed using Pretty or a suitable Rich representation
    - For RequestFinished events, output is printed only if raw mode is enabled (using Pretty formatting).
    - Report events (info, success, error, etc.) are always printed with appropriate styling.
    """

    def __init__(self, raw_mode=False):
        from janito.cli.console import shared_console

        self.console = shared_console
        self.raw_mode = raw_mode
        import janito.report_events as report_events

        import janito.tools.tool_events as tool_events

        super().__init__(driver_events, report_events, tool_events, agent_events)
        self._waiting_printed = False

    def on_RequestStarted(self, event):
        # Print waiting message with provider and model name
        provider = None
        model = None
        if hasattr(event, "payload") and isinstance(event.payload, dict):
            provider = event.payload.get("provider_name")
            model = event.payload.get("model") or event.payload.get("model_name")
        if not provider:
            provider = getattr(event, "provider_name", None)
        if not provider:
            provider = getattr(event, "driver_name", None)
        if not provider:
            provider = "LLM"
        if not model:
            model = getattr(event, "model", None)
        if not model:
            model = getattr(event, "model_name", None)
        if not model:
            model = "?"
        self.console.print(
            f"[bold cyan]Waiting for {provider} (model: {model})...[/bold cyan]", end=""
        )
        self._waiting_printed = True

    def on_AgentWaitingForResponse(self, event):
        # Agent waiting - set flag but don't print anything
        self._waiting_printed = True

    def on_ResponseReceived(self, event):
        parts = event.parts if hasattr(event, "parts") else None
        if not parts:
            self.console.print("[No response parts to display]")
            self.console.file.flush()
            return
        for part in parts:
            if isinstance(part, message_parts.TextMessagePart):
                self.console.print(Markdown(part.content))
                self.console.file.flush()

    def delete_current_line(self):
        """
        Clears the entire current line in the terminal and returns the cursor to column 1.
        """
        # Use raw ANSI escape sequences but write directly to the underlying file
        # to bypass Rich's escaping/interpretation
        if hasattr(self.console, 'file') and hasattr(self.console.file, 'write'):
            self.console.file.write("\r\033[2K")
            self.console.file.flush()
        else:
            # Fallback to sys.stdout if console.file is not available
            import sys
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()

    def on_RequestFinished(self, event):
        if self._waiting_printed:
            self.delete_current_line()
            self._waiting_printed = False

    def on_AgentReceivedResponse(self, event):
        # Clear any waiting message when agent receives response
        if self._waiting_printed:
            self.delete_current_line()
            self._waiting_printed = False

    def on_ToolCallError(self, event):
        # Optionally handle tool call errors in a user-friendly way
        error = getattr(event, "error", None)
        tool = getattr(event, "tool_name", None)
        if error and tool:
            self.console.print(f"[bold red]Tool Error ({tool}):[/] {error}")
            self.console.file.flush()

    def on_ReportEvent(self, event):
        # Special handling for security-related report events
        subtype = getattr(event, "subtype", None)
        msg = getattr(event, "message", None)
        action = getattr(event, "action", None)
        tool = getattr(event, "tool", None)
        context = getattr(event, "context", None)
        if (
            subtype == ReportSubtype.ERROR
            and msg
            and "[SECURITY] Path access denied" in msg
        ):
            # Highlight security errors with a distinct style
            self.console.print(
                Panel(f"{msg}", title="[red]SECURITY VIOLATION[/red]", style="bold red")
            )
            self.console.file.flush()
            return

        msg = event.message if hasattr(event, "message") else None
        subtype = event.subtype if hasattr(event, "subtype") else None
        if not msg or not subtype:
            return
        if subtype == ReportSubtype.ACTION_INFO:
            # Clear any waiting message before showing action info
            if self._waiting_printed:
                self.delete_current_line()
                self._waiting_printed = False
            # Use orange for all write/modification actions
            modification_actions = (
                getattr(ReportAction, "UPDATE", None),
                getattr(ReportAction, "WRITE", None),
                getattr(ReportAction, "DELETE", None),
                getattr(ReportAction, "CREATE", None),
            )
            style = (
                "orange1"
                if getattr(event, "action", None) in modification_actions
                else "cyan"
            )
            self.console.print(Text(msg, style=style), end="")
            self.console.file.flush()
        elif subtype in (
            ReportSubtype.SUCCESS,
            ReportSubtype.ERROR,
            ReportSubtype.WARNING,
        ):
            self.console.print(msg)
            self.console.file.flush()
        elif subtype == ReportSubtype.STDOUT:
            print(msg)
        elif subtype == ReportSubtype.STDERR:
            print(msg, file=sys.stderr)
        else:
            self.console.print(msg)
            self.console.file.flush()
