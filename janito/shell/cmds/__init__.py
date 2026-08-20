"""
Shell commands package.
"""

# Import all command handlers to register them
from . import (
    api_types,
    ask,
    changes,
    exit,
    help,
    history,
    mcp,
    model,
    multi,
    plugins,
    price,
    priv,
    prompt,
    provider,
    read,
    rewind,
    show_tools_stats,
    skills,
    status,
    thinking,
    tools,
    write,
)
from .base import CmdHandler
from .registry import get_registered_commands, register_command

__all__ = [
    "CmdHandler",
    "api_types",
    "ask",
    "changes",
    "exit",
    "get_registered_commands",
    "help",
    "history",
    "mcp",
    "model",
    "multi",
    "plugins",
    "price",
    "priv",
    "prompt",
    "provider",
    "read",
    "register_command",
    "rewind",
    "show_tools_stats",
    "skills",
    "status",
    "thinking",
    "tools",
    "write",
]
