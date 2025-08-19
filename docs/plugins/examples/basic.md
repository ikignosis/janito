# Basic Plugin Example

## Overview

This example demonstrates a simple plugin that provides basic greeting functionality. It illustrates the fundamental concepts of plugin development in Janito.

## Plugin Code

```python
from janito.plugins.base import Plugin, PluginMetadata
from janito.tools.tool_base import ToolBase, ToolPermissions

# Define a simple greeting tool
class GreetingTool(ToolBase):
    tool_name = "greet"
    permissions = ToolPermissions(read=True, write=False, execute=True)
    
    def run(self, name: str = "World", style: str = "friendly") -> str:
        """Generate a greeting message with optional style."""
        styles = {
            "friendly": f"Hello, {name}! 👋",
            "formal": f"Good day, {name}.",
            "enthusiastic": f"Hey {name}! Great to see you! 🎉"
        }
        return styles.get(style, styles["friendly"])

# Define the plugin
class BasicPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="basic",
            version="1.0.0",
            description="A basic greeting plugin",
            author="Janito Team",
            license="MIT"
        )
    
    def get_tools(self):
        return [GreetingTool]

# Register the plugin
class PLUGIN_CLASS(BasicPlugin):
    pass
```

## Configuration

To enable this plugin, add it to your `janito.json`:

```json
{
  "plugins": {
    "load": {
      "basic": true
    }
  }
}
```

## Usage

Once enabled, you can use the greet tool:

```json
{
  "tool": "greet",
  "name": "Alice",
  "style": "enthusiastic"
}
```

Expected output: "Hey Alice! Great to see you! 🎉"

## Key Concepts Demonstrated

- **Plugin Class**: Inheriting from `Plugin` base class
- **Tool Definition**: Creating a tool by extending `ToolBase`
- **Metadata**: Providing plugin information through `get_metadata()`
- **Tool Registration**: Returning tools from `get_tools()`
- **Permissions**: Setting appropriate tool permissions

This basic example provides a foundation for more complex plugin development, showing the essential structure and components needed for a working plugin.