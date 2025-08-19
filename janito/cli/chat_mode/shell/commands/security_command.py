"""Security command group for chat mode."""

from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler as BaseCommand
from janito.cli.chat_mode.shell.commands.security.allowed_sites import (
    SecurityAllowedSitesCommand,
)


class SecurityCommand(BaseCommand):
    """Security management command group."""

    def get_name(self) -> str:
        return "security"

    def get_description(self) -> str:
        return "Security management commands"

    def get_usage(self):
        return """
Usage: /security <subcommand> [args...]

Subcommands:
  allowed-sites    Manage allowed sites for fetch_url tool
  
Examples:
  /security allowed-sites list
  /security allowed-sites add tradingview.com
  /security allowed-sites remove yahoo.com
"""

    def __init__(self, after_cmd_line=None, shell_state=None):
        super().__init__(after_cmd_line=after_cmd_line, shell_state=shell_state)
        self.subcommands = {
            "allowed-sites": SecurityAllowedSitesCommand(
                after_cmd_line=after_cmd_line, shell_state=shell_state
            )
        }

    def run(self):
        """Execute the security command."""
        args = self.after_cmd_line.strip().split()

        if not args:
            print(self.get_usage())
            return

        subcommand = args[0].lower()
        if subcommand in self.subcommands:
            # Pass the remaining args to the subcommand
            remaining_args = " ".join(args[1:]) if len(args) > 1 else ""
            self.subcommands[subcommand].after_cmd_line = remaining_args
            self.subcommands[subcommand].run()
        else:
            print(f"Error: Unknown security subcommand '{subcommand}'")
            print(self.get_usage())
