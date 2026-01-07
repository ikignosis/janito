class ToolRunException(Exception):
    """
    Exception raised when a tool runs but fails due to an internal error or runtime exception.
    This is distinct from ToolRunError event, which is for event bus notification.
    """

    def __init__(self, tool_name, error, arguments=None, exception=None):
        self.tool_name = tool_name
        self.error = error
        self.arguments = arguments
        self.original_exception = exception
        super().__init__(f"ToolRunException: {tool_name}: {error}")
