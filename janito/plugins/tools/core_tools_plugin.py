"""
Core tools plugin implementation.
"""

from functools import wraps
from typing import Type
from janito.plugin_system.base import Plugin, PluginMetadata

from .ask_user import AskUser
from .copy_file import CopyFile
from .create_directory import CreateDirectory
from .create_file import CreateFile
from .delete_text_in_file import DeleteTextInFile
from .fetch_url import FetchUrl
from .find_files import FindFiles
from .move_file import MoveFile
from .open_html_in_browser import OpenHtmlInBrowser
from .open_url import OpenUrl
from .python_code_run import PythonCodeRun
from .python_command_run import PythonCommandRun
from .python_file_run import PythonFileRun
from .read_chart import ReadChart
from .read_files import ReadFiles
from .remove_directory import RemoveDirectory
from .remove_file import RemoveFile
from .replace_text_in_file import ReplaceTextInFile
from .run_bash_command import RunBashCommand
from .run_powershell_command import RunPowershellCommand
from .show_image import ShowImage
from .show_image_grid import ShowImageGrid
from .view_file import ViewFile
from .validate_file_syntax.core import ValidateFileSyntax
from .get_file_outline.core import GetFileOutline
from .search_text.core import SearchText
from .decorators import get_core_tools

# Registry for core tools
_core_tools_registry = []


def register_core_tool(cls: Type):
    """Decorator to register a core tool."""
    _core_tools_registry.append(cls)
    return cls


class CoreToolsPlugin(Plugin):
    """Core tools plugin providing essential janito functionality."""

    def get_metadata(self):
        return PluginMetadata(
            name="core_tools",
            version="1.0.0",
            description="Core tools for file operations, code execution, and system interactions",
            author="janito team",
            license="MIT",
        )

    def get_tools(self):
        return [
            AskUser,
            CopyFile,
            CreateDirectory,
            CreateFile,
            DeleteTextInFile,
            FetchUrl,
            FindFiles,
            MoveFile,
            OpenHtmlInBrowser,
            OpenUrl,
            PythonCodeRun,
            PythonCommandRun,
            PythonFileRun,
            ReadChart,
            ReadFiles,
            RemoveDirectory,
            RemoveFile,
            ReplaceTextInFile,
            RunBashCommand,
            RunPowershellCommand,
            ShowImage,
            ShowImageGrid,
            ViewFile,
            ValidateFileSyntax,
            GetFileOutline,
            SearchText,
        ] + get_core_tools()
