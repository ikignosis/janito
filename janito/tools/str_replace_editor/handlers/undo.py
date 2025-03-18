"""
Handler for the undo_edit command in str_replace_editor.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.rich_console import print_info, print_success, print_error, print_warning
from ..utils import normalize_path, _file_history

def handle_undo_edit(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Undo the last edit made to a file using in-memory history.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file whose last edit should be undone
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    
    print_info(f"Undoing last edit to file: {path}", "Undo Operation")
    
    if not path:
        print_error("Missing required parameter: path", "Error")
        return ("Missing required parameter: path", True)
    
    # Store the original path for display purposes
    original_path = path
    
    # Normalize the path (converts to absolute path)
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    # Check if file exists
    if not file_path.exists():
        print_error(f"File {path} does not exist", "Error")
        return (f"File {path} does not exist", True)
    
    # Check in-memory history
    if path not in _file_history or not _file_history[path]:
        print_warning(f"Warning: No edit history for file {path}")
        return (f"No edit history for file {path}", True)
    
    try:
        # Get the last content
        last_content = _file_history[path].pop()
        
        # Write the last content back to the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(last_content)
        
        # Show relative path if it's not an absolute path in the original input
        display_path = original_path if os.path.isabs(original_path) else os.path.relpath(file_path, get_config().workspace_dir)
        success_msg = f"Successfully reverted the last edit made to the file {display_path}"
        print_success(success_msg, "Success")
        return (success_msg, False)
    except Exception as e:
        display_path = original_path if os.path.isabs(original_path) else os.path.relpath(file_path, get_config().workspace_dir)
        error_msg = f"Error undoing edit to file {display_path}: {str(e)}"
        print_error(error_msg, "Error")
        return (error_msg, True)