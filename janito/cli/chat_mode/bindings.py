"""
Key bindings for Janito Chat CLI.
"""

from prompt_toolkit.key_binding import KeyBindings
from janito.tools.permissions import get_global_allowed_permissions


class KeyBindingsFactory:
    @staticmethod
    def create():
        bindings = KeyBindings()

        @bindings.add("c-y")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "Yes"
            buf.validate_and_handle()

        @bindings.add("c-n")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "No"
            buf.validate_and_handle()

        @bindings.add("f2")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "/restart"
            buf.validate_and_handle()

        @bindings.add("f12")
        def _(event):
            buf = event.app.current_buffer
            buf.text = "Do It"
            buf.validate_and_handle()

        @bindings.add("enter", eager=True)
        def _(event):
            """Handle Enter key to interrupt current request."""
            import threading

            # Get the current session context
            from prompt_toolkit.application import get_app

            app = get_app()

            # Use global cancellation manager for robust cancellation
            from janito.llm.cancellation_manager import get_cancellation_manager

            cancel_manager = get_cancellation_manager()

            cancelled = cancel_manager.cancel_current_request()
            if cancelled:
                # Provide user feedback
                from rich.console import Console

                console = Console()
                console.print("[red]Request cancelled by Enter key[/red]")

                # Prevent the Enter key from being processed as input
                event.app.output.flush()
                return

            # If no active request to cancel, let normal Enter behavior proceed

        return bindings
