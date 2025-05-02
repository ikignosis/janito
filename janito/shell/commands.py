from janito.agent.tool_registry import get_tool_schemas
from rich.console import Console


def handle_command(cmd, console: Console, shell_state=None):
    cmd = cmd.strip().lower()
    if cmd in ("/exit", "exit"):
        return "exit"
    if cmd in ("/help", "help"):
        console.print("[bold cyan]/help[/]: Show this help message")
        console.print("[bold cyan]/exit[/]: Exit the shell")
        console.print("[bold cyan]/tools[/]: List available tools")
        return
    if cmd in ("/tools", "tools"):
        table = None
        try:
            from rich.table import Table

            table = Table(
                title="Available Tools", show_lines=True, style="bold magenta"
            )
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="green")
            table.add_column("Parameters", style="yellow")
            for schema in get_tool_schemas():
                fn = schema["function"]
                params = "\n".join(
                    [
                        f"[bold]{k}[/]: {v['type']}"
                        for k, v in fn["parameters"].get("properties", {}).items()
                    ]
                )
                table.add_row(f"[b]{fn['name']}[/b]", fn["description"], params or "-")
        except Exception as e:
            console.print(f"[red]Error loading tools: {e}[/red]")
        if table:
            console.print(table)
        return
    # Unknown command
    console.print(f"[yellow]Unknown command:[/] {cmd}")
