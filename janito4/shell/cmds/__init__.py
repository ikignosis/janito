"""
Shell commands package.
"""

from .registry import register_command, get_registered_commands
from .base import CmdHandler

# Import all command handlers to register them
from . import config
from . import exit

__all__ = ["CmdHandler", "get_registered_commands", "register_command"]
