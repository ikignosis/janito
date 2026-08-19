"""
/thinking command handler - enables or disables thinking mode for the current session.

Usage:
    /thinking            - Show the current thinking status
    /thinking on|off     - Enable or disable runtime config thinking for the current session

The switch is **runtime-only**: it updates the shell's thinking state for the
running session, but it does **not** change any persisted configuration.
"""

from ...provider_accessors import get_gemini_flavor_from_provider
from .base import CmdHandler
from .registry import register_command


class ThinkingCmdHandler(CmdHandler):
    """Command handler for /thinking command."""

    @property
    def name(self) -> str:
        return "/thinking"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /thinking command."""
        parts = user_input.strip().split(None, 1)
        if not parts or parts[0].lower() != self.name.lower():
            return False

        if len(parts) == 1:
            self._show_status(shell)
        else:
            self._set_thinking(shell, parts[1].strip())
        return True

    @staticmethod
    def _show_status(shell) -> None:
        """Print the current thinking status and usage."""
        provider = getattr(shell, "provider", None)
        if provider and get_gemini_flavor_from_provider(provider):
            print(
                "Thinking mode is N/A for this session "
                "(controlled via Reasoning Level for Gemini models)."
            )
            print("Usage: /thinking on|off")
            return
        current = getattr(shell, "thinking", False)
        status_str = "enabled (on)" if current else "disabled (off)"
        print(f"Thinking mode is currently {status_str} for this session.")
        print("Usage: /thinking on|off")

    @staticmethod
    def _set_thinking(shell, mode: str) -> None:
        """Enable or disable thinking for this shell session."""
        mode_lower = mode.lower()
        if mode_lower == "on":
            shell.thinking = True
            print(
                "[OK] Thinking mode enabled for this session "
                "(config default unchanged)."
            )
            provider = getattr(shell, "provider", None)
            if provider and get_gemini_flavor_from_provider(provider):
                print(
                    "[WARN] Gemini models reason by default; thinking depth is controlled "
                    "via reasoning level rather than the thinking flag."
                )
        elif mode_lower == "off":
            shell.thinking = False
            print(
                "[OK] Thinking mode disabled for this session "
                "(config default unchanged)."
            )
            provider = getattr(shell, "provider", None)
            if provider and get_gemini_flavor_from_provider(provider):
                print(
                    "[WARN] Gemini models reason by default; thinking depth is controlled "
                    "via reasoning level rather than the thinking flag."
                )
        else:
            print(
                f"Error: Invalid option '{mode}'. Use '/thinking on' or '/thinking off'."
            )


# Register this handler
_handler = ThinkingCmdHandler()
register_command(_handler)
