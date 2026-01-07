"""Management of disabled tools configuration."""


class DisabledToolsState:
    """Singleton to manage disabled tools configuration."""

    _instance = None
    _disabled_tools = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_disabled_tools(cls):
        """Get the set of disabled tool names."""
        return cls._disabled_tools.copy()

    @classmethod
    def set_disabled_tools(cls, tool_names):
        """Set the disabled tools from a list or set of tool names."""
        if isinstance(tool_names, str):
            tool_names = [
                name.strip() for name in tool_names.split(",") if name.strip()
            ]
        cls._disabled_tools = set(tool_names)

    @classmethod
    def is_tool_disabled(cls, tool_name):
        """Check if a specific tool is disabled."""
        return tool_name in cls._disabled_tools

    @classmethod
    def disable_tool(cls, tool_name):
        """Add a tool to the disabled list."""
        cls._disabled_tools.add(tool_name)

    @classmethod
    def enable_tool(cls, tool_name):
        """Remove a tool from the disabled list."""
        cls._disabled_tools.discard(tool_name)


# Convenience functions
def get_disabled_tools():
    """Get the current set of disabled tools."""
    return DisabledToolsState.get_disabled_tools()


def set_disabled_tools(tool_names):
    """Set the disabled tools from a list, set, or comma-separated string."""
    DisabledToolsState.set_disabled_tools(tool_names)


def is_tool_disabled(tool_name):
    """Check if a specific tool is disabled."""
    return DisabledToolsState.is_tool_disabled(tool_name)


def load_disabled_tools_from_config():
    """Load disabled tools from global config."""
    from janito.config import config

    disabled_str = config.get("disabled_tools", "")
    if disabled_str:
        DisabledToolsState.set_disabled_tools(disabled_str)
    return DisabledToolsState.get_disabled_tools()
