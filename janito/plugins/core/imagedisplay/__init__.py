"""
Image Display Plugin - Core plugin for displaying images inline in the terminal.

This plugin provides tools for displaying images directly in the terminal using
rich library's image rendering capabilities.
"""

from .plugin import ImageDisplayPlugin

# Plugin metadata for discovery/listing
__plugin_name__ = "core.imagedisplay"
__plugin_description__ = "Display images inline in the terminal using rich"

__all__ = ["ImageDisplayPlugin"]
