"""
Base classes for janito plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Type, Union
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from janito.tools.tool_base import ToolBase


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""

    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    homepage: Optional[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class PluginResource:
    """Represents a resource provided by a plugin."""

    name: str
    type: str  # "tool", "command", "config"
    description: str
    schema: Optional[Dict[str, Any]] = None


class Plugin(ABC):
    """
    Base class for all janito plugins.

    Plugins can provide tools, commands, or other functionality.
    """

    def __init__(self):
        self.metadata: PluginMetadata = self.get_metadata()

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return metadata describing this plugin."""
        pass

    def get_tools(self) -> List[Type["ToolBase"]]:
        """
        Return a list of tool classes provided by this plugin.

        Returns:
            List of ToolBase subclasses that should be registered
        """
        return []

    def get_commands(self) -> Dict[str, Any]:
        """
        Return a dictionary of CLI commands provided by this plugin.

        Returns:
            Dict mapping command names to command handlers
        """
        return {}

    def initialize(self) -> None:
        """
        Called when the plugin is loaded.
        Override to perform any initialization needed.
        """
        pass

    def cleanup(self) -> None:
        """
        Called when the plugin is unloaded.
        Override to perform any cleanup needed.
        """
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for plugin configuration.

        Returns:
            JSON schema dict describing configuration options
        """
        return {}

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration dict to validate

        Returns:
            True if configuration is valid
        """
        return True

    def get_resources(self) -> List[PluginResource]:
        """
        Return a list of resources provided by this plugin.

        Returns:
            List of PluginResource objects describing the resources
        """
        resources = []

        # Add tools as resources
        for tool_class in self.get_tools():
            tool_instance = tool_class()
            tool_name = getattr(tool_instance, "tool_name", tool_class.__name__)
            tool_desc = getattr(tool_class, "__doc__", f"Tool: {tool_name}")
            resources.append(
                PluginResource(
                    name=tool_name,
                    type="tool",
                    description=tool_desc or f"Tool provided by {self.metadata.name}",
                )
            )

        # Add commands as resources
        commands = self.get_commands()
        for cmd_name, cmd_handler in commands.items():
            cmd_desc = getattr(cmd_handler, "__doc__", f"Command: {cmd_name}")
            resources.append(
                PluginResource(
                    name=cmd_name,
                    type="command",
                    description=cmd_desc or f"Command provided by {self.metadata.name}",
                )
            )

        # Add config schema as resource
        config_schema = self.get_config_schema()
        if config_schema:
            resources.append(
                PluginResource(
                    name=f"{self.metadata.name}_config",
                    type="config",
                    description=f"Configuration schema for {self.metadata.name} plugin",
                    schema=config_schema,
                )
            )

        return resources
