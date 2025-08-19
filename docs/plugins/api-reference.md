# Plugin API Reference

## Overview

This document provides a comprehensive reference for the Janito plugin API. It details the classes, methods, and interfaces available for plugin development.

## Core Classes

### PluginMetadata

Data class containing plugin metadata.

```python
@dataclass
class PluginMetadata:
    name: str                    # Unique plugin identifier
    version: str                 # Semantic version (e.g., "1.0.0")
    description: str             # Brief description of the plugin
    author: str                  # Plugin author name
    license: str = "MIT"         # Software license
    homepage: Optional[str] = None  # URL to plugin documentation
    dependencies: List[str] = None  # List of required packages
```

### PluginResource

Represents a resource provided by a plugin.

```python
@dataclass
class PluginResource:
    name: str                    # Resource name
    type: str                    # Resource type ("tool", "command", "config")
    description: str             # Resource description
    schema: Optional[Dict[str, Any]] = None  # JSON schema for config resources
```

### Plugin (Abstract Base Class)

Base class for all plugins.

```python
class Plugin(ABC):
    def __init__(self):
        self.metadata: PluginMetadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return metadata describing this plugin."""
    
    def get_tools(self) -> List[Type[ToolBase]]:
        """Return a list of tool classes provided by this plugin."""
    
    def get_commands(self) -> Dict[str, Any]:
        """Return a dictionary of CLI commands provided by this plugin."""
    
    def initialize(self) -> None:
        """Called when the plugin is loaded. Override for initialization."""
    
    def cleanup(self) -> None:
        """Called when the plugin is unloaded. Override for cleanup."""
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
    
    def get_resources(self) -> List[PluginResource]:
        """Return a list of resources provided by this plugin."""
```

## Plugin Lifecycle

### Initialization

The `initialize()` method is called when the plugin is loaded:

```python
def initialize(self) -> None:
    """Called when the plugin is loaded."""
    # Perform any setup needed
    self.setup_database_connection()
    self.load_configuration()
```

### Cleanup

The `cleanup()` method is called when the plugin is unloaded:

```python
def cleanup(self) -> None:
    """Called when the plugin is unloaded."""
    # Perform any cleanup needed
    self.close_database_connection()
    self.cleanup_temp_files()
```

## Resource Contribution Methods

### get_tools()

Returns a list of tool classes that should be registered:

```python
def get_tools(self) -> List[Type[ToolBase]]:
    return [MyTool1, MyTool2, MyTool3]
```

### get_commands()

Returns a dictionary mapping command names to handler functions:

```python
def get_commands(self) -> Dict[str, Any]:
    return {
        "mycommand": self.handle_mycommand,
        "another-command": self.handle_another_command
    }
```

### get_config_schema()

Returns a JSON schema describing the plugin's configuration options:

```python
def get_config_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "timeout": {
                "type": "number",
                "minimum": 1,
                "maximum": 3600,
                "default": 30
            },
            "api_key": {
                "type": "string",
                "minLength": 32
            }
        },
        "required": ["api_key"]
    }
```

## Utility Methods

### get_config()

Retrieves the plugin's current configuration:

```python
def get_config(self) -> Dict[str, Any]:
    """Get the current plugin configuration."""
    # Implementation provided by the plugin system
    pass
```

### report_action()

Logs an action performed by a tool (available in ToolBase):

```python
def report_action(self, message: str, action_type: str = "action") -> None:
    """Report an action performed by the tool."""
    # Implementation provided by the base class
    pass
```

## Best Practices

### Error Handling

Always include proper error handling in your tools:

```python
class MyTool(ToolBase):
    def run(self, param: str) -> str:
        try:
            # Your logic here
            result = some_operation(param)
            return f"Success: {result}"
        except ValueError as e:
            return f"Error: Invalid parameter - {str(e)}"
        except Exception as e:
            return f"Error: Operation failed - {str(e)}"
```

### Documentation

Include comprehensive docstrings for all methods:

```python
def run(self, name: str = "World") -> str:
    """
    Generate a greeting message.
    
    Args:
        name: Name of the person to greet (default: "World")
    
    Returns:
        Formatted greeting message
    
    Examples:
        >>> tool = GreetingTool()
        >>> tool.run("Alice")
        'Hello, Alice!'
    """
```

### Security

Follow security best practices:

- Validate all inputs
- Use appropriate permissions for tools
- Sanitize user input
- Implement timeouts for long-running operations
- Avoid executing untrusted code

This API reference provides the complete interface for developing plugins, enabling you to create powerful extensions that integrate seamlessly with the Janito system.