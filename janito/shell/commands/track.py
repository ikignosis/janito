from janito.agent.tool_use_tracker import ToolUseTracker
from rich.console import Console
from rich.table import Table


def handle_track(console: Console, args=None, shell_state=None):
    tracker = ToolUseTracker.instance()
    history = tracker.get_history()
    if not history:
        console.print("[bold yellow]No tool usage history found.[/bold yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Tool")
    table.add_column("Params/Result")
    for idx, entry in enumerate(history, 1):
        tool = entry["tool"]
        params = entry["params"].copy()
        result = entry.get("result", "")
        # For create/replace file, trim content in params only
        if tool in ("create_file", "replace_file") and "content" in params:
            content = params["content"]
            if isinstance(content, str):
                lines = content.splitlines()
                if len(lines) > 3:
                    params["content"] = (
                        "\n".join(lines[:2])
                        + f"\n... (trimmed, {len(lines)} lines total)"
                    )
                elif len(content) > 120:
                    params["content"] = content[:120] + "... (trimmed)"
                else:
                    params["content"] = content
        param_result = f"{params}\n--- Result ---\n{result}" if result else str(params)
        table.add_row(str(idx), tool, param_result)
    console.print(table)
