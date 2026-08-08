"""
/tools command handler - displays all loaded tools.
"""

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


def _print_builtin_tools(builtin_tools, builtin_schemas) -> None:
    """Print the built-in tools section."""
    print("\n[Built-in Tools]")
    print("-" * 40)
    if builtin_tools:
        for name in sorted(builtin_tools.keys()):
            schema = builtin_schemas.get(name, {})
            description = _truncate(schema.get("description", "No description"))
            print(f"  {name:<25} {description}")
    else:
        print("  (none loaded)")


def _print_skipped_tools() -> None:
    """Print tools skipped during discovery (failed should_load() validation)."""
    try:
        from janito.tools import get_skipped_tools

        skipped_tools = get_skipped_tools()
    except Exception:
        skipped_tools = {}
    if skipped_tools:
        print("\n[Skipped Tools]")
        print("-" * 40)
        for name, reason in sorted(skipped_tools.items()):
            print(f"  {name:<25} {reason}")


def _print_mcp_tools(mcp_tools) -> None:
    """Print the MCP tools section."""
    print("\n[MCP Tools]")
    print("-" * 40)
    if mcp_tools:
        for tool in sorted(mcp_tools, key=lambda x: x["name"]):
            name = tool["name"]
            description = tool.get("description", "No description")
            # Remove the [service] prefix from description for cleaner display
            if description.startswith("[") and "] " in description:
                description = description.split("] ", 1)[1]
            print(f"  {name:<25} {_truncate(description)}")
    else:
        print("  (no MCP services connected)")


class ToolsCmdHandler(CmdHandler):
    """Command handler for /tools command."""

    @property
    def name(self) -> str:
        return "/tools"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /tools command."""
        if user_input.lower() == self.name.lower():
            self._print_tools()
            return True
        return False

    def _print_tools(self) -> None:
        """Print information about all available tools."""
        print()
        print("=" * 60)
        print("Available Tools")
        print("=" * 60)

        # Get built-in tools from tools_registry
        builtin_tools, builtin_schemas = _load_builtin_tools()

        # Get MCP tools from MCP manager
        mcp_tools = _load_mcp_tools()

        # Print sections
        _print_builtin_tools(builtin_tools, builtin_schemas)
        _print_skipped_tools()
        _print_mcp_tools(mcp_tools)

        # Summary
        total_tools = len(builtin_tools) + len(mcp_tools)
        print()
        print(
            f"Total: {total_tools} tools ({len(builtin_tools)} built-in, {len(mcp_tools)} MCP)"
        )
        print("=" * 60)
        print()


# Register this handler
_handler = ToolsCmdHandler()
register_command(_handler)
