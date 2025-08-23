"""
Plugin System for Development Tools

This package organizes all available tools into logical plugin groups
for easier discovery and usage.
"""

__version__ = "1.0.0"
__author__ = "Development Assistant"

from .core import filemanager, codeanalyzer, system, imagedisplay
from .web import webtools
from .dev import pythondev, visualization
from .ui import userinterface

# Plugin registry
PLUGINS = {
    "core.filemanager": filemanager,
    "core.codeanalyzer": codeanalyzer,
    "core.system": system,
    "core.imagedisplay": imagedisplay,
    "web.webtools": webtools,
    "dev.pythondev": pythondev,
    "dev.visualization": visualization,
    "ui.userinterface": userinterface,
}


def list_plugins():
    """Return all available plugins"""
    return list(PLUGINS.keys())


def get_plugin(name):
    """Get a specific plugin by name"""
    return PLUGINS.get(name)
