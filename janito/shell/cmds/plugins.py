"""
/plugins command handler - lists installed plugins.

Usage:
    /plugins    - List all installed plugins

The command scans the plugins directory (``<config_dir>/plugins``, default
``~/.janito/plugins``) and shows each installed plugin, its path and
whether it was loaded in the current session (cross-referenced with the
plugins loaded by ``janito.plugin_manager.load_plugins`` /
``load_installed_plugins``).
"""

from rich.console import Console
from rich.table import Table

from janito.plugin_manager import (
    LOADED_PLUGINS,
    get_default_plugins_dir,
    scan_installed_plugins,
)

from .base import CmdHandler
from .registry import register_command


class PluginsCmdHandler(CmdHandler):
    """Command handler for /plugins command."""

    @property
    def name(self) -> str:
        return "/plugins"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /plugins command."""
        if user_input.lower().strip() == self.name.lower():
            self._print_plugins()
            return True
        return False

    def _print_plugins(self) -> None:
        """Print information about installed plugins as a rich table."""
        console = Console(markup=False)
        plugins_dir = get_default_plugins_dir()
        installed = scan_installed_plugins()

        # Map plugin directory paths to the Plugin objects loaded this
        # session so the status column can reflect load errors.
        loaded_by_path = {str(p.path.resolve()): p for p in LOADED_PLUGINS}

        if not installed:
            table = Table(
                title="Installed Plugins",
                title_style="bold",
                header_style="bold cyan",
                show_header=False,
                box=None,
                pad_edge=False,
            )
            table.add_column("Key", style="green", no_wrap=True)
            table.add_column("Value", overflow="fold")
            table.add_row("Status", "No plugins installed.")
            table.add_row("Install", "janito --install-plugin <github_url>")
            table.add_row("Load", "janito --plugin <plugin_dir>")
            table.add_row("Plugins dir", str(plugins_dir))
            console.print(table)
            return

        table = Table(
            title="Installed Plugins",
            title_style="bold",
            header_style="bold cyan",
        )
        table.add_column("Plugin", style="green", no_wrap=True)
        table.add_column("Path", overflow="fold")
        table.add_column("Status", no_wrap=True)

        for name, path in installed:
            loaded = loaded_by_path.get(str(path.resolve()))
            if loaded is None:
                status = "Not loaded"
            elif loaded.load_error is None:
                status = "Loaded"
            else:
                status = f"ERROR: {loaded.load_error}"
            table.add_row(name, str(path), status)

        console.print(table)
        print(f"Plugins dir: {plugins_dir}")


# Register this handler
_handler = PluginsCmdHandler()
register_command(_handler)
