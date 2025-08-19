class BaseTool:
    """Base class for all tools."""

    tool_name: str = ""

    def __init__(self):
        if not self.tool_name:
            self.tool_name = self.__class__.__name__.lower()

    def run(self, *args, **kwargs) -> str:
        """Execute the tool."""
        raise NotImplementedError
