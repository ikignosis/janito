"""
Key bindings for Janito Chat CLI.
"""

from prompt_toolkit.key_binding import KeyBindings
from janito.tooling.permissions import get_global_allowed_permissions


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

        return bindings
