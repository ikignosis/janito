"""
Handler for the insert command in str_replace_editor.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.rich_console import print_info, print_success, print_error
from janito.tools.usage_tracker import get_tracker
from ..utils import normalize_path, _file_history

def handle_insert(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Insert text at a specific location in a file.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file to modify
            - insert_line: The line number after which to insert the text
            - new_str: The text to insert
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    insert_line = args.get("insert_line")
    new_str = args.get("new_str")
    
    # Count lines in new string
    new_lines_count = len(new_str.splitlines()) if new_str else 0
    
    print_info(f"Inserting text in file: {path}, after line {insert_line} (+{new_lines_count} lines)", "Insert Operation")
    
    if not path:
        print_error("Missing required parameter: path", "Error")
        return ("Missing required parameter: path", True)
    if insert_line is None:
        print_error("Missing required parameter: insert_line", "Error")
        return ("Missing required parameter: insert_line", True)
    if new_str is None:
        print_error("Missing required parameter: new_str", "Error")
        return ("Missing required parameter: new_str", True)
    
    # Store the original path for display purposes
    original_path = path
    
    # Normalize the path (converts to absolute path)
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        print_error(f"File {path} does not exist", "Error")
        return (f"File {path} does not exist", True)
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = "".join(lines)
        
        # Save the current content for undo
        if path not in _file_history:
            _file_history[path] = []
        _file_history[path].append(content)
        
        # Check if insert_line is valid
        if insert_line < 0 or insert_line > len(lines):
            print_error(f"Invalid insert line {insert_line} for file {path}", "Error")
            return (f"Invalid insert line {insert_line} for file {path}", True)
        
        # Ensure new_str ends with a newline if it doesn't already
        if new_str and not new_str.endswith('\n'):
            new_str += '\n'
        
        # Insert the new string
        lines.insert(insert_line, new_str)
        
        # Track the number of lines inserted
        lines_count = len(new_str.splitlines())
        get_tracker().increment('lines_replaced', lines_count)
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        # Show relative path if it's not an absolute path in the original input
        display_path = original_path if os.path.isabs(original_path) else os.path.relpath(file_path, get_config().workspace_dir)
        
        # If the response is too long, truncate it
        response = f"Successfully inserted text at line {insert_line} in file {display_path}"
        print_success(response, "Success")
        if len(response) > 1000:  # Arbitrary limit for demonstration
            return (response[:1000] + "\n<response clipped>", False)
            
        return (response, False)
    except Exception as e:
        display_path = original_path if os.path.isabs(original_path) else os.path.relpath(file_path, get_config().workspace_dir)
        error_msg = f"Error inserting text in file {display_path}: {str(e)}"
        print_error(error_msg, "Error")
        return (error_msg, True)