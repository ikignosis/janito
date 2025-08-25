"""
Image Display Plugin implementation.
"""

from typing import Dict, Any, List, Type

from janito.plugin_system.base import Plugin, PluginMetadata
from janito.tools.tool_base import ToolBase
from .tools.show_image import ShowImageTool
from .tools.show_image_grid import ShowImageGridTool


class ImageDisplayPlugin(Plugin):
    """Plugin for displaying images inline in the terminal using rich."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="core.imagedisplay",
            version="1.0.0",
            description="Display images inline in the terminal using rich",
            author="Janito",
            dependencies=["rich", "pillow"],
        )

    def get_tools(self) -> List[Type[ToolBase]]:
        # Return tool classes so the PluginManager can register them
        return [ShowImageTool, ShowImageGridTool]

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "default_width": {
                    "type": "integer",
                    "description": "Default width for image display",
                    "minimum": 1,
                    "maximum": 200,
                },
                "default_height": {
                    "type": "integer",
                    "description": "Default height for image display",
                    "minimum": 1,
                    "maximum": 100,
                },
                "preserve_aspect": {
                    "type": "boolean",
                    "description": "Preserve aspect ratio by default",
                    "default": True,
                },
            },
        }
