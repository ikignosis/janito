"""
CLI Command: List available tools
"""


def _group_tools_by_permission(tools, tool_instances, disabled_tools):
    read_only_tools = []
    write_only_tools = []
    read_write_tools = []
    exec_tools = []
    import inspect

    for tool in tools:
        # Skip disabled tools entirely
        if tool in disabled_tools:
            continue

        inst = tool_instances.get(tool, None)
        param_names = []
        if inst and hasattr(inst, "run"):
            sig = inspect.signature(inst.run)
            param_names = [p for p in sig.parameters if p != "self"]

        info = {
            "name": tool,
            "params": ", ".join(param_names),
            "tool_name": tool,
            "disabled": False,
        }
        perms = getattr(inst, "permissions", None)
        if perms and perms.execute:
            exec_tools.append(info)
        elif perms and perms.read and perms.write:
            read_write_tools.append(info)
        elif perms and perms.read:
            read_only_tools.append(info)
        elif perms and perms.write:
            write_only_tools.append(info)
    return read_only_tools, write_only_tools, read_write_tools, exec_tools


def _print_tools_table(console, title, tools_info):
    from rich.table import Table

    table = Table(
        title=title, show_header=True, header_style="bold", show_lines=False, box=None
    )
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Parameters", style="yellow")
    for info in tools_info:
        table.add_row(info["name"], info["params"] or "-")
    console.print(table)


def handle_list_tools(args=None):
    from janito.plugins.tools.local.adapter import LocalToolsAdapter
    import janito.tools  # Ensure all tools are registered
    from janito.tools.tool_base import ToolPermissions

    read = getattr(args, "read", False) if args else False
    write = getattr(args, "write", False) if args else False
    execute = getattr(args, "exec", False) if args else False
    if not (read or write or execute):
        read = write = execute = True
    from janito.tools.permissions import set_global_allowed_permissions

    set_global_allowed_permissions(
        ToolPermissions(read=read, write=write, execute=execute)
    )
    # Load disabled tools from config
    from janito.tools.disabled_tools import DisabledToolsState
    from janito.config import config

    disabled_str = config.get("disabled_tools", "")
    if disabled_str:
        DisabledToolsState.set_disabled_tools(disabled_str)
    disabled_tools = DisabledToolsState.get_disabled_tools()

    registry = janito.tools.local_tools_adapter
    tools = registry.list_tools()
    if tools:
        from rich.console import Console

        console = Console()
        tool_instances = {t.tool_name: t for t in registry.get_tools()}
        read_only_tools, write_only_tools, read_write_tools, exec_tools = (
            _group_tools_by_permission(tools, tool_instances, disabled_tools)
        )
        if read_only_tools:
            _print_tools_table(console, "Read-only tools (-r)", read_only_tools)
        if write_only_tools:
            _print_tools_table(console, "Write-only tools (-w)", write_only_tools)
        if read_write_tools:
            _print_tools_table(console, "Read-Write tools (-rw)", read_write_tools)
        if exec_tools:
            _print_tools_table(console, "Execution tools (-x)", exec_tools)
    else:
        print("No tools registered.")
    return
