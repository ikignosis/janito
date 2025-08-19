# Plugin Development Guide

## Overview

This guide provides comprehensive instructions for developing plugins for the Janito system. Plugins allow you to extend functionality by adding custom tools, commands, and features.

## Plugin Structure

A plugin consists of a Python class that inherits from `Plugin` and implements the required methods. Plugins are typically organized in the `plugins/` directory with a hierarchical structure:

```
plugins/
└── myplugin/
    ├── __init__.py
    └── tools/
        └── mytool.py
```

## Basic Plugin Example

```python
from janito.plugins.base import Plugin, PluginMetadata
from janito.tools.tool_base import ToolBase, ToolPermissions

# Define a tool
class HelloWorldTool(ToolBase):
    tool_name = "hello_world"
    permissions = ToolPermissions(read=True, write=False, execute=True)
    
    def run(self, name: str = "World") -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"

# Define the plugin
class MyPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="myplugin",
            version="1.0.0",
            description="My custom plugin",
            author="Your Name",
            license="MIT"
        )
    
    def get_tools(self):
        return [HelloWorldTool]

# Register the plugin
class PLUGIN_CLASS(MyPlugin):
    pass
```

## Plugin Metadata

The `get_metadata()` method returns a `PluginMetadata` object with the following fields:

- **name**: Unique plugin identifier
- **version**: Semantic version (e.g., "1.0.0")
- **description**: Brief description of the plugin
- **author**: Plugin author name
- **license**: Software license (default: "MIT")
- **homepage**: URL to plugin documentation
- **dependencies**: List of required packages

## Resource Contribution

Plugins contribute resources through several methods:

### Tools

The primary way plugins extend functionality is through tools. Tools are classes that inherit from `ToolBase` and implement the `run()` method.

```python
def get_tools(self) -> List[Type[ToolBase]]:
    return [MyTool1, MyTool2]
```

### Commands

Plugins can add CLI commands:

```python
def get_commands(self) -> Dict[str, Any]:
    return {"mycommand": my_command_function}
```

### Configuration

Plugins can define configuration schemas:

```python
def get_config_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "api_key": {"type": "string", "description": "Your API key"}
        }
    }
```

## Plugin Lifecycle

Plugins have several lifecycle methods:

- **initialize()**: Called when the plugin is loaded
- **cleanup()**: Called when the plugin is unloaded
- **get_metadata()**: Returns plugin metadata
- **get_tools()**: Returns tool classes

## Development Best Practices

- **Clear Naming**: Use descriptive names for plugins and tools
- **Documentation**: Include docstrings for all methods and classes
- **Error Handling**: Implement proper error handling in tools
- **Security**: Validate inputs and use appropriate permissions
- **Testing**: Write tests for your plugin functionality

## Testing Plugins

Create a test file for your plugin:

```python
# test_myplugin.py
def test_hello_world_tool():
    tool = HelloWorldTool()
    result = tool.run("Test")
    assert "Hello, Test!" in result
```

## Distribution

To share your plugin:

1. Package it as a Git repository
2. Include documentation
3. Add to the official plugins repository or share independently

## Advanced Features

### Plugin Resources

Plugins can explicitly declare the resources they provide:

```python
def get_resources(self) -> List[PluginResource]:
    return [
        PluginResource(
            name="hello_world",
            type="tool",
            description="Says hello to someone"
        )
    ]
```

### Dependency Management

Specify dependencies in the metadata:

```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="myplugin",
        version="1.0.0",
        description="Plugin with dependencies",
        author="You",
        dependencies=["requests>=2.25.0", "pydantic"]
    )
```

This comprehensive guide covers the essentials of plugin development, enabling you to create powerful extensions for the Janito system.