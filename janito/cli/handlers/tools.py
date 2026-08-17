"""Tool and MCP listing CLI handlers."""

from ...mcp_config import get_mcp_config_path, list_services
from ...mcp_manager import get_mcp_manager
from ...tooling.tools_registry import get_all_tool_permissions, get_all_tool_schemas


def _categorize_tools(schemas, permissions) -> dict[str, list[dict]]:
    """Group tools by category based on name prefixes."""
    categories = {
        "File Operations": [],
        "System Operations": [],
        "Code Search Operations": [],
        "Email Operations": [],
        "Other": [],
    }

    for schema in schemas:
        func_info = schema["function"]
        name = func_info["name"]
        perms = permissions.get(name, "")

        # Get parameter names only
        params = func_info["parameters"]["properties"]
        tool_info = {"name": name, "permissions": perms, "params": list(params.keys())}

        if (
            name.startswith(
                (
                    "Create",
                    "Delete",
                    "List",
                    "Read",
                    "Remove",
                    "Replace",
                    "Search",
                    "Move",
                )
            )
            and "Email" not in name
        ):
            categories["File Operations"].append(tool_info)
        elif name.startswith(("Get", "Run")):
            categories["System Operations"].append(tool_info)
        elif name == "CodeSearch":
            categories["Code Search Operations"].append(tool_info)
        elif (
            name.startswith(("Send", "Read", "Compose", "SearchEmail"))
            or "Email" in name
        ):
            categories["Email Operations"].append(tool_info)
        else:
            categories["Other"].append(tool_info)

    return categories


def _print_categories(categories: dict[str, list[dict]]) -> None:
    """Display tools grouped by category as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console(markup=False)
    for category, tools_list in categories.items():
        if not tools_list:
            continue
        table = Table(
            title=category,
            title_style="bold",
            header_style="bold cyan",
        )
        table.add_column("Tool", style="green", no_wrap=True)
        table.add_column("Permissions", no_wrap=True)
        table.add_column("Parameters", overflow="fold")

        for tool in sorted(tools_list, key=lambda x: x["name"]):
            perms_str = tool["permissions"] or "-"
            params_str = ", ".join(tool["params"]) if tool["params"] else "(no params)"
            table.add_row(tool["name"], perms_str, params_str)

        console.print(table)


def handle_list_tools(args) -> int:
    """Handle --list-tools command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from rich.console import Console
    from rich.table import Table

    schemas = get_all_tool_schemas()
    permissions = get_all_tool_permissions()

    categories = _categorize_tools(schemas, permissions)
    _print_categories(categories)

    table = Table(
        title="Available Tools",
        title_style="bold",
        header_style="bold cyan",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_column("Key", style="green", no_wrap=True)
    table.add_column("Value")
    table.add_row("Total", str(len(schemas)))
    table.add_row("Permission codes", "r=read, w=write, x=execute")
    Console(markup=False).print(table)

    return 0


def _mcp_service_rows(
    manager, name: str, config: dict
) -> tuple[str, str, str, str, str]:
    """Build the (name, transport, status, config, tools) row for one MCP service."""
    transport = config.get("transport", "unknown")
    connected = name in manager.connected_services
    status = "[connected]" if connected else "[not connected]"

    if transport == "stdio":
        config_display = f"Command: {config.get('command', '')}"
    elif transport == "http":
        config_display = f"URL: {config.get('url', '')}"
        headers = config.get("headers", {})
        if headers:
            config_display += f"; {len(headers)} header(s)"
    else:
        import json

        config_display = json.dumps(config)

    tools_display = ""
    if connected:
        # Get tools for this service
        try:
            # Refresh tools to get updated list
            tools = manager.get_all_tools(force_refresh=True)
            service_tools = [
                t
                for t in tools
                if t.get("function", {}).get("name", "").startswith(f"{name}_")
            ]
            tool_names = []
            for tool in service_tools:
                func = tool.get("function", {})
                tool_name = func.get("name", "")
                # Remove prefix for display
                display_name = tool_name[len(name) + 1 :] if tool_name else tool_name
                tool_names.append(display_name)
            if tool_names:
                tools_display = ", ".join(tool_names)
        except Exception as e:
            tools_display = f"Error loading tools: {e}"

    return name, transport, status, config_display, tools_display


def handle_list_mcp(args) -> int:
    """Handle --list-mcp command.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success)
    """
    from rich.console import Console
    from rich.table import Table

    services = list_services()

    console = Console(markup=False)

    if not services:
        print("MCP Services: none configured")
        print(f"Config file: {get_mcp_config_path()}")
        print()
        print("  Use /mcp add to configure MCP services in interactive mode")
        return 0

    # Load MCP manager to get tools
    manager = get_mcp_manager()
    manager.load_services()

    table = Table(
        title="MCP Services",
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Service", style="green", no_wrap=True)
    table.add_column("Transport", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Config", overflow="fold")

    for name, config in services.items():
        row = _mcp_service_rows(manager, name, config)
        table.add_row(*row[:4])
        if row[4]:
            table.add_row("", "", "", f"Tools: {row[4]}")

    manager.unload_all()

    console.print(table)
    print(f"Config file: {get_mcp_config_path()}")

    return 0
