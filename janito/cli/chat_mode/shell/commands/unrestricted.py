"""Unrestricted mode command for chat mode."""

from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


class UnrestrictedShellHandler(ShellCmdHandler):
    """Toggle unrestricted mode (equivalent to -u CLI flag)."""

    help_text = "Toggle unrestricted mode (disable path security and URL whitelist)"

    def run(self):
        """Execute the unrestricted command."""
        if not self.shell_state:
            shared_console.print("[red]Error: Shell state not available[/red]")
            return

        # Toggle unrestricted mode
        current_unrestricted = getattr(self.shell_state, "unrestricted_mode", False)
        new_unrestricted = not current_unrestricted

        # Update shell state
        self.shell_state.unrestricted_mode = new_unrestricted

        # Update tools adapter
        if hasattr(self.shell_state, "tools_adapter"):
            setattr(
                self.shell_state.tools_adapter, "unrestricted_paths", new_unrestricted
            )

        # Update URL whitelist manager
        from janito.tools.url_whitelist import get_url_whitelist_manager

        whitelist_manager = get_url_whitelist_manager()
        whitelist_manager.set_unrestricted_mode(new_unrestricted)

        status = "enabled" if new_unrestricted else "disabled"
        warning = (
            " (DANGEROUS - no path or URL restrictions)" if new_unrestricted else ""
        )

        shared_console.print(
            f"[bold {'red' if new_unrestricted else 'green'}]"
            f"Unrestricted mode {status}{warning}[/bold {'red' if new_unrestricted else 'green'}]"
        )
