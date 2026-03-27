"""
/tools command handler - displays all loaded tools.
"""

from .base import CmdHandler
from .registry import register_command


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
        try:
            from janito.tooling.tools_registry import get_all_tools, get_all_tool_schemas
            builtin_tools = get_all_tools()
            builtin_schemas = {s["function"]["name"]: s["function"] for s in get_all_tool_schemas()}
        except Exception as e:
            builtin_tools = {}
            builtin_schemas = {}
            print(f"Warning: Could not load built-in tools: {e}")
        
        # Get MCP tools from MCP manager
        mcp_tools = []
        try:
            from janito.mcp_manager import get_mcp_manager
            mcp_manager = get_mcp_manager()
            if mcp_manager:
                mcp_tool_schemas = mcp_manager.get_all_tools()
                for schema in mcp_tool_schemas:
                    mcp_tools.append(schema["function"])
        except Exception as e:
            print(f"Warning: Could not load MCP tools: {e}")
        
        # Print built-in tools section
        if builtin_tools:
            print("\n[Built-in Tools]")
            print("-" * 40)
            for name in sorted(builtin_tools.keys()):
                schema = builtin_schemas.get(name, {})
                description = schema.get("description", "No description")
                # Truncate long descriptions
                if len(description) > 60:
                    description = description[:57] + "..."
                print(f"  {name:<25} {description}")
        else:
            print("\n[Built-in Tools]")
            print("  (none loaded)")
        
        # Print MCP tools section
        if mcp_tools:
            print("\n[MCP Tools]")
            print("-" * 40)
            for tool in sorted(mcp_tools, key=lambda x: x["name"]):
                name = tool["name"]
                description = tool.get("description", "No description")
                # Remove the [service] prefix from description for cleaner display
                if description.startswith("[") and "] " in description:
                    description = description.split("] ", 1)[1]
                # Truncate long descriptions
                if len(description) > 60:
                    description = description[:57] + "..."
                print(f"  {name:<25} {description}")
        else:
            print("\n[MCP Tools]")
            print("  (no MCP services connected)")
        
        # Summary
        total_tools = len(builtin_tools) + len(mcp_tools)
        print()
        print(f"Total: {total_tools} tools ({len(builtin_tools)} built-in, {len(mcp_tools)} MCP)")
        print("=" * 60)
        print()


# Register this handler
_handler = ToolsCmdHandler()
register_command(_handler)
