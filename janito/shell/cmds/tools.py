"""
/tools command handler - displays all loaded tools.
"""

from rich.console import Console
from rich.table import Table

from .base import CmdHandler
from .registry import register_command


def _load_builtin_tools():
    """Load built-in tools and their schemas from the tools registry."""
    try:
        from janito.tooling.tools_registry import get_all_tool_schemas, get_all_tools

        builtin_tools = get_all_tools()
        builtin_schemas = {
            s["function"]["name"]: s["function"] for s in get_all_tool_schemas()
        }
    except Exception as e:
        builtin_tools = {}
        builtin_schemas = {}
        print(f"Warning: Could not load built-in tools: {e}")
    return builtin_tools, builtin_schemas


def _load_mcp_tools():
    """Load MCP tool schemas from the MCP manager."""
    mcp_tools = []
    try:
        from janito.mcp_manager import get_mcp_manager

        mcp_manager = get_mcp_manager()
        if mcp_manager:
            for schema in mcp_manager.get_all_tools():
                mcp_tools.append(schema["function"])
    except Exception as e:
        print(f"Warning: Could not load MCP tools: {e}")
    return mcp_tools


def _truncate(description: str) -> str:
    """Truncate a tool description to 60 chars for display."""
    if len(description) > 60:
        return description[:57] + "..."
    return description


def _tools_table(title: str, rows: list[tuple[str, str]]) -> None:
    """Print a Tool/Description table (or a friendly message when empty)."""
    console = Console(markup=False)
    if not rows:
        print(f"{title}: (none)")
        return
    table = Table(
        title=title,
        title_style="bold",
        header_style="bold cyan",
    )
    table.add_column("Tool", style="green", no_wrap=True)
    table.add_column("Description", overflow="fold")
    for name, description in rows:
        table.add_row(name, description)
    console.print(table)


class ToolsCmdHandler(CmdHandler):
    """Command handler for /tools command."""

    @property
    def name(self) -> str:
        return "/tools"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /tools command."""
        if user_input.strip().lower() == self.name.lower():
            self._print_tools()
            return True
        return False

    def _print_tools(self) -> None:
        """Print information about all available tools as rich tables."""
        # Warn when tool loading is disabled via --no-tools.
        from janito.tooling.tools_registry import tools_loading_enabled

        if not tools_loading_enabled():
            Console().print(
                "[bold yellow]Warning:[/bold yellow] tool loading is disabled "
                "(--no-tools). Only the skill tools are available "
                "(load_skill, read_skill_resource)."
            )

        # Get built-in tools from tools_registry
        builtin_tools, builtin_schemas = _load_builtin_tools()

        # Get MCP tools from MCP manager
        mcp_tools = _load_mcp_tools()

        # Print sections
        builtin_rows = []
        if builtin_tools:
            for name in sorted(builtin_tools.keys()):
                schema = builtin_schemas.get(name, {})
                description = _truncate(schema.get("description", "No description"))
                builtin_rows.append((name, description))
        _tools_table("Built-in Tools", builtin_rows)

        skipped_rows = []
        try:
            from janito.tools import get_skipped_tools

            skipped_tools = get_skipped_tools()
        except Exception:
            skipped_tools = {}
        for name, reason in sorted(skipped_tools.items()):
            skipped_rows.append((name, reason))
        _tools_table("Skipped Tools", skipped_rows)

        mcp_rows = []
        for tool in sorted(mcp_tools, key=lambda x: x["name"]):
            name = tool["name"]
            description = tool.get("description", "No description")
            # Remove the [service] prefix from description for cleaner display
            if description.startswith("[") and "] " in description:
                description = description.split("] ", 1)[1]
            mcp_rows.append((name, _truncate(description)))
        _tools_table("MCP Tools", mcp_rows)

        # Summary
        total_tools = len(builtin_tools) + len(mcp_tools)
        summary = Table(
            title="Summary",
            title_style="bold",
            header_style="bold cyan",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        summary.add_column("Key", style="green", no_wrap=True)
        summary.add_column("Value")
        summary.add_row(
            "Total",
            f"{total_tools} tools ({len(builtin_tools)} built-in, {len(mcp_tools)} MCP)",
        )
        Console(markup=False).print(summary)


# Register this handler
_handler = ToolsCmdHandler()
register_command(_handler)
