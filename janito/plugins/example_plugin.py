"""
Example plugin demonstrating the plugin system.
"""

from janito.plugin_system.base import Plugin, PluginMetadata, PluginResource
from janito.tools.tool_base import ToolBase, ToolPermissions
from typing import Dict, Any


class HelloWorldTool(ToolBase):
    """A simple tool that says hello."""

    tool_name = "hello_world"
    permissions = ToolPermissions(read=True, write=False, execute=True)

    def run(self, name: str = "World") -> str:
        """
        Say hello to someone.

        Args:
            name: Name of the person to greet

        Returns:
            Greeting message
        """
        self.report_action(f"Saying hello to {name}", "greet")
        return f"Hello, {name}!"


class CalculatorTool(ToolBase):
    """A simple calculator tool."""

    tool_name = "calculator"
    permissions = ToolPermissions(read=True, write=False, execute=True)

    def run(self, operation: str, a: float, b: float) -> str:
        """
        Perform basic calculations.

        Args:
            operation: Operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number

        Returns:
            Result as string
        """
        self.report_action(f"Calculating {a} {operation} {b}", "calculate")

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            result = a / b
        else:
            return f"Error: Unknown operation '{operation}'"

        return str(result)


class ExamplePlugin(Plugin):
    """Example plugin providing basic tools."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="example",
            version="1.0.0",
            description="Example plugin with basic tools",
            author="Janito Team",
            license="MIT",
            homepage="https://github.com/janito/example-plugin",
        )

    def get_tools(self):
        return [HelloWorldTool, CalculatorTool]

    def initialize(self):
        print("Example plugin initialized!")

    def cleanup(self):
        print("Example plugin cleaned up!")

    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
        return {
            "type": "object",
            "properties": {
                "greeting_prefix": {
                    "type": "string",
                    "description": "Custom greeting prefix for hello_world tool",
                    "default": "Hello",
                },
                "max_calculation": {
                    "type": "number",
                    "description": "Maximum allowed calculation result",
                    "default": 1000000,
                },
            },
        }


# This makes the plugin discoverable
PLUGIN_CLASS = ExamplePlugin
