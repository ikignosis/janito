class ToolCallException(Exception):
    """
    Exception raised when a tool call fails (e.g., not found, invalid arguments, invocation failure).
    This is distinct from ToolCallError event, which is for event bus notification.
    """

    def __init__(self, tool_name, error, arguments=None, exception=None):
        self.tool_name = tool_name
        self.error = error
        self.arguments = arguments
        self.original_exception = exception

        # Build detailed error message
        details = []
        details.append(f"ToolCallException: {tool_name}: {error}")

        if arguments is not None:
            details.append(f"Arguments received: {arguments}")
            if isinstance(arguments, dict):
                details.append("Parameters:")
                for key, value in arguments.items():
                    details.append(f"  {key}: {repr(value)} ({type(value).__name__})")
            elif isinstance(arguments, (list, tuple)):
                details.append(f"Positional arguments: {arguments}")
                for i, value in enumerate(arguments):
                    details.append(f"  [{i}]: {repr(value)} ({type(value).__name__})")
            else:
                details.append(
                    f"Single argument: {repr(arguments)} ({type(arguments).__name__})"
                )

        super().__init__("\n".join(details))


class MissingProviderSelectionException(Exception):
    """
    Raised when no provider is specified and no default provider is set.
    """

    def __init__(self, configured=None, supported=None):
        self.configured = configured or []
        self.supported = supported or []
        super().__init__("No provider specified and no default provider is set.")
