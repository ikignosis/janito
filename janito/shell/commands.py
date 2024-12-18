"""Command definitions for Janito shell."""
from typing import Dict, Optional
from dataclasses import dataclass
from rich.console import Console
from janito.shell.registry import Command, CommandRegistry, get_path_completer
from . import handlers

# Command class moved to registry.py

def register_commands() -> None:
    """Register all available commands."""
    registry = CommandRegistry()

    # Register commands with their completers
    registry.register(Command("/clear", "Clear the terminal screen", None, handlers.handle_clear))
    registry.register(Command("/request", "Submit a change request", "/request <change request text>", handlers.handle_request))
    registry.register(Command("/ask", "Ask a question about the codebase", "/ask <question>", handlers.handle_ask))
    registry.register(Command("/quit", "Exit the shell", None, handlers.handle_exit))
    registry.register(Command("/help", "Show help for commands", "/help [command]", handlers.handle_help))
    registry.register(Command("/include", "Set paths to include in analysis", "/include <path1> [path2 ...]",
                            handlers.handle_include, lambda: get_path_completer(False)))
    registry.register(Command("/rinclude", "Set paths to include recursively in analysis", "/rinclude <path1> [path2 ...]",
                            handlers.handle_rinclude, lambda: get_path_completer(True)))

    # Register aliases
    registry.register_alias("clear", "/clear")
    registry.register_alias("quit", "/quit")
    registry.register_alias("help", "/help")
    registry.register_alias("/inc", "/include")
    registry.register_alias("/rinc", "/rinclude")