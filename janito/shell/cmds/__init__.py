"""
Shell commands package.
"""

# Import all command handlers to register them
from . import (
    ask,
    config,
    exit,
    help,
    history,
    mcp,
    multi,
    priv,
    prompt,
    rollback,
    show_tools_stats,
    tools,
)
from .base import CmdHandler
from .registry import get_registered_commands, register_command

__all__ = [
    "CmdHandler",
    "ask",
    "config",
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
    "show_tools_stats",
    "tools",
]
