"""
Command registry for shell commands.
"""

from .base import CmdHandler

_commands: list[CmdHandler] = []


def register_command(handler: CmdHandler) -> None:
    """Register a command handler."""
    _commands.append(handler)


def get_registered_commands() -> list[CmdHandler]:
    """Get all registered command handlers."""
    return list(_commands)
