"""Prompt creation and configuration for Janito shell."""
from typing import Dict, Any
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import NestedCompleter
from rich import print as rich_print
from janito.config import config
from .registry import CommandRegistry

def create_shell_completer(registry: CommandRegistry):
    """Create command completer for shell with nested completions."""
    if config.debug:
        rich_print("[yellow]Creating shell completer...[/yellow]")

    commands = registry.get_commands()

    if config.debug:
        rich_print(f"[yellow]Found {len(commands)} commands for completion[/yellow]")

    # Create nested completions for commands
    completions: Dict[str, Any] = {}
    
    for cmd_name, cmd in commands.items():
        if config.debug:
            rich_print(f"[yellow]Setting up completion for command: {cmd_name}[/yellow]")
        completions[cmd_name] = cmd.completer

    if config.debug:
        rich_print("[yellow]Creating nested completer from completions dictionary[/yellow]")
    return NestedCompleter.from_nested_dict(completions)

def create_shell_session(registry: CommandRegistry) -> PromptSession:
    """Create and configure the shell prompt session."""
    if config.debug:
        rich_print("[yellow]Creating shell session...[/yellow]")

    history_file = Path.home() / ".janito_history"
    if config.debug:
        rich_print(f"[yellow]Using history file: {history_file}[/yellow]")

    completer = create_shell_completer(registry)

    return PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
        complete_while_typing=True
    )