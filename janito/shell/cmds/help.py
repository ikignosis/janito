"""
/help command handler - displays all available commands.
"""

from rich.console import Console
from rich.table import Table

from .base import CmdHandler
from .registry import get_registered_commands, register_command


class HelpCmdHandler(CmdHandler):
    """Command handler for /help command."""

    @property
    def name(self) -> str:
        return "/help"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /help command."""
        if user_input.lower() == self.name.lower():
            self._print_help()
            return True
        return False

    def _print_help(self) -> None:
        """Print help information for all available commands as rich tables."""
        commands = get_registered_commands()

        console = Console(markup=False)

        table = Table(
            title="Available Commands",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Command", style="green", no_wrap=True)
        for cmd in commands:
            table.add_row(cmd.name)
        console.print(table)

        features = Table(
            title="Additional features",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        features.add_column("Key", style="green", no_wrap=True)
        features.add_column("Description", overflow="fold")
        features.add_row("!<command>", "Execute a shell command directly")
        features.add_row("/prompt", "Show the system prompt")
        features.add_row("/skills", "List all available skills")
        features.add_row("/tools", "List all available tools")
        features.add_row("/plugins", "List all installed plugins")
        features.add_row(
            "/read", "Ask the LLM using the main history but read-only tools"
        )
        features.add_row(
            "/write", "Ask the LLM using the main history but write-only tools"
        )
        features.add_row("/show_tools_stats", "Show tool usage statistics")
        features.add_row(
            "/changes", "Show the file-changing tool executions for this prompt"
        )
        features.add_row(
            "/multi", "Enable multiline input for next prompt (ESC ENTER to submit)"
        )
        features.add_row(
            "/thinking on|off",
            "Enable or disable thinking mode for the current session",
        )
        console.print(features)

        shortcuts = Table(
            title="Keyboard shortcuts",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        shortcuts.add_column("Key", style="green", no_wrap=True)
        shortcuts.add_column("Description", overflow="fold")
        shortcuts.add_row("[F2]", "Restart conversation")
        shortcuts.add_row("[F12]", "Do It (continue existing plan)")
        console.print(shortcuts)

        mcp = Table(
            title="MCP Services",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        mcp.add_column("Command", style="green", no_wrap=True)
        mcp.add_column("Description", overflow="fold")
        mcp.add_row("/mcp add <name> stdio <cmd>", "Add stdio service")
        mcp.add_row("/mcp add <name> http <url>", "Add HTTP service")
        mcp.add_row("/mcp list", "List MCP services")
        mcp.add_row("/mcp remove <name>", "Remove an MCP service")
        console.print(mcp)


# Register this handler
_handler = HelpCmdHandler()
register_command(_handler)
