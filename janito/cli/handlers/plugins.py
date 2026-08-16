"""Plugin listing CLI handler."""

from ...plugin_manager import LOADED_PLUGINS


def handle_list_plugins(args) -> int:
    """Handle --list-plugins command.

    Displays the plugins loaded via ``--plugin`` (registered by
    ``janito.plugin_manager.load_plugins``) and any ``on_start`` errors.

    Args:
        args: Parsed command line arguments (unused).

    Returns:
        int: Exit code (0 on success).
    """
    from rich.console import Console
    from rich.table import Table

    console = Console(markup=False)

    if not LOADED_PLUGINS:
        table = Table(
            title="Loaded Plugins",
            title_style="bold",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Key", style="green", no_wrap=True)
        table.add_column("Value", overflow="fold")
        table.add_row("Status", "No plugins loaded.")
        table.add_row("Load a plugin", "janito --plugin <plugin_dir>")
        console.print(table)
        return 0

    table = Table(
        title="Loaded Plugins",
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Plugin", style="green", no_wrap=True)
    table.add_column("Path", overflow="fold")
    table.add_column("Status", no_wrap=True)

    for plugin in LOADED_PLUGINS:
        if plugin.load_error is None:
            status = "OK"
        else:
            status = f"ERROR: {plugin.load_error}"
        table.add_row(plugin.name, str(plugin.path), status)

    console.print(table)
    return 0
