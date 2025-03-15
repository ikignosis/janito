"""
Main module for implementing the Claude text editor functionality.
"""
from typing import Dict, Any, Tuple
from .handlers import (
    handle_create,
    handle_view,
    handle_str_replace,
    handle_insert,
    handle_undo_edit
)
from .utils import normalize_path
from janito.tools.decorators import tool_meta

@tool_meta(label="Editing file: {file_path} ({command})")
def str_replace_editor(**kwargs) -> Tuple[str, bool]:
    """
    Handle text editor tool requests from Claude.
    Implements the Claude text editor tool specification.
    
    Args:
        **kwargs: All arguments passed to the tool, including:
            - command: The command to execute (view, create, str_replace, insert, undo_edit)
            - path: Path to the file
            - Additional command-specific arguments
        
    Returns:
        A tuple containing (message, is_error)
    """
    command = kwargs.get("command")
    
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
