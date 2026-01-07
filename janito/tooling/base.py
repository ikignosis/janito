class BaseTool:
    """Base class for all tools."""

    @property
    def tool_name(self) -> str:
        """Derive tool name from class name by convention."""
        # Convert class name to snake_case and remove 'tool' suffix if present
        class_name = self.__class__.__name__
        if class_name.endswith('Tool'):
            class_name = class_name[:-4]
        
        # Convert CamelCase to snake_case
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        return name

    def run(self, *args, **kwargs) -> str:
        """Execute the tool."""
        raise NotImplementedError
