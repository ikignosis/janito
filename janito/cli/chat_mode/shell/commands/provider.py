from janito.cli.core.getters import get_current_provider
from janito.cli.core.setters import set_provider
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console as console


class ProviderCmdHandler(ShellCmdHandler):
    """Handler for the /provider command to view or change the current provider."""

    help_text = "Manage the current LLM provider. Usage: /provider [provider_name]"

    def run(self):
        """Execute the provider command."""
        if not self.after_cmd_line.strip():
            # No argument provided, show current provider
            current = get_current_provider()
            console.print(f"[bold]Current provider:[/bold] {current}")
            return

        # Argument provided, attempt to change provider
        new_provider = self.after_cmd_line.strip()
        try:
            set_provider(new_provider)
            console.print(
                f"[bold green]Provider changed to:[/bold green] {new_provider}"
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
