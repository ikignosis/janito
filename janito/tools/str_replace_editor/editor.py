"""
Main module for implementing the Claude text editor functionality.
"""
from typing import Tuple
from janito.config import get_config
from .handlers import (
    handle_create,
    handle_view,
    handle_str_replace,
    handle_insert,
    handle_undo_edit
)

def str_replace_editor(**kwargs) -> Tuple[str, bool]:
    """
    Custom editing tool for viewing, creating and editing files
    * State is persistent across command calls and discussions with the user
    * If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
    * The `create` command cannot be used if the specified `path` already exists as a file
    * If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
    * The `undo_edit` command will revert the last edit made to the file at `path`
    * When in ask mode, only the `view` command is allowed

    Notes for using the `str_replace` command:
    * The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
    * If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
    * The `new_str` parameter should contain the edited lines that should replace the `old_str`
    
    Args:
        **kwargs: All arguments passed to the tool, including:
            - command: The command to execute (view, create, str_replace, insert, undo_edit)
            - path: Path to the file
            - Additional command-specific arguments
        
    Returns:
        A tuple containing (message, is_error)
    """
    command = kwargs.get("command")
    
    # If in ask mode, only allow view operations
    if get_config().ask_mode and command != "view":
        return ("Cannot perform file modifications in ask mode. Use --ask option to disable modifications.", True)
    
    if command == "create":
        return handle_create(kwargs)
    elif command == "view":
        return handle_view(kwargs)
    elif command == "str_replace":
        return handle_str_replace(kwargs)
    elif command == "insert":
        return handle_insert(kwargs)
    elif command == "undo_edit":
        return handle_undo_edit(kwargs)
    else:
        return (f"Command '{command}' not implemented yet", True)
