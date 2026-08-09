"""
Shell commands package.
"""

# Import all command handlers to register them
from . import (
    btw,
    changes,
    exit,
    help,
    history,
    mcp,
    multi,
    priv,
    prompt,
    rollback,
    show_config,
    show_tools_stats,
    tools,
)
from .base import CmdHandler
from .registry import get_registered_commands, register_command

__all__ = [
    "CmdHandler",
    "btw",
    "changes",
    "exit",
    "get_registered_commands",
    "help",
    "history",
    "mcp",
    "multi",
    "priv",
    "prompt",
    "register_command",
    "rollback",
    "show_config",
    "show_tools_stats",
    "tools",
]
