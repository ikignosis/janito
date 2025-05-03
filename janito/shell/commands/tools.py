from janito.agent.tool_registry import get_tool_schemas
from rich.table import Table


def handle_tools(console, args=None, shell_state=None):
    table = Table(title="Available Tools", show_lines=True, style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Parameters", style="yellow")
    try:
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
        return
    console.print(table)


handle_tools.help_text = "List available tools"
