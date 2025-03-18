"""
Handler for the str_replace command in str_replace_editor.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.rich_console import print_info, print_success, print_error
from janito.tools.usage_tracker import get_tracker, count_lines_in_string
from ..utils import normalize_path, _file_history

def handle_str_replace(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Replace a specific string in a file with a new string.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file to modify
            - old_str: The text to replace (must match EXACTLY)
            - new_str: The new text to insert
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    old_str = args.get("old_str")
    new_str = args.get("new_str", "")  # new_str can be empty to effectively delete text
    
    # Count lines in old and new strings
    old_lines_count = len(old_str.splitlines()) if old_str else 0
    new_lines_count = len(new_str.splitlines()) if new_str else 0
    line_delta = new_lines_count - old_lines_count
    delta_sign = "+" if line_delta > 0 else "" if line_delta == 0 else "-"
    
    print_info(f"Replacing text in file: {path} ({old_lines_count} -> {new_lines_count} lines, {delta_sign}{abs(line_delta)})", "Replacing text in file")
    
    if not path:
        print_error("Missing required parameter: path", "Error")
        return ("Missing required parameter: path", True)
    if old_str is None:
        print_error("Missing required parameter: old_str", "Error")
        return ("Missing required parameter: old_str", True)
    
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        print_error(f"File {path} does not exist", "Error")
        return (f"File {path} does not exist", True)
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Save the current content for undo
        if path not in _file_history:
            _file_history[path] = []
        _file_history[path].append(content)
        
        # Check if old_str exists in the content (must match EXACTLY)
        if old_str not in content:
            print_error("No exact match found for replacement. Please check your text and ensure whitespaces match exactly.", "Error")
            return ("Error: No exact match found for replacement. Please check your text and ensure whitespaces match exactly.", True)
        
        # Count occurrences to check for multiple matches
        match_count = content.count(old_str)
        if match_count > 1:
            print_error(f"Found {match_count} matches for replacement text. The old_str parameter is not unique in the file. Please include more context to make it unique.", "Error")
            return (f"Error: Found {match_count} matches for replacement text. The old_str parameter is not unique in the file. Please include more context to make it unique.", True)
        
        # Replace the string
        new_content = content.replace(old_str, new_str)
        
        # Track the number of lines replaced and the line delta
        lines_changed, line_delta = count_lines_in_string(old_str, new_str)
        get_tracker().increment('lines_replaced', lines_changed)
        get_tracker().increment('lines_delta', line_delta)
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Show relative path if it's not an absolute path in the original input
        display_path = args.get("path") if os.path.isabs(args.get("path")) else os.path.relpath(file_path, get_config().workspace_dir)
        print_success(f"", "Success")
        return (f"Successfully replaced string in file {display_path}", False)
    except Exception as e:
        # Show relative path if it's not an absolute path in the original input
        display_path = args.get("path") if os.path.isabs(args.get("path")) else os.path.relpath(file_path, get_config().workspace_dir)
        print_error(f"Error replacing string in file {display_path}: {str(e)}", "Error")
        return (f"Error replacing string in file {display_path}: {str(e)}", True)