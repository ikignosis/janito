"""
Interactive shell module using prompt_toolkit.
"""

from .interactive import InteractiveShell

# Import cmds subpackage
from . import cmds

__all__ = ["InteractiveShell", "cmds"]
