"""
Command handlers for the str_replace_editor package.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from .utils import normalize_path, _file_history, backup_file, get_backup_info

def handle_create(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Create a new file with the specified content.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file to create
            - file_text: Content to write to the file
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    file_text = args.get("file_text", "")
    
    if not path:
        return ("Missing required parameter: path", True)
    
    path = normalize_path(path)
    
    # Convert to Path object for better path handling
    file_path = pathlib.Path(path)
    
    # Check if the file already exists
    if file_path.exists():
        return (f"File {path} already exists", True)
    
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the content to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_text)
        # Show relative path if it's not an absolute path
        display_path = path if os.path.isabs(path) else os.path.relpath(file_path, get_config().workspace_dir)
        return (f"Successfully created file {display_path}", False)
    except Exception as e:
        return (f"Error creating file {path}: {str(e)}", True)


def handle_view(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    View the contents of a file or list directory contents.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file or directory to view
            - view_range (optional): Array of two integers specifying start and end line numbers
        
    Returns:
        A tuple containing (content_or_message, is_error)
    """
    path = args.get("path")
    view_range = args.get("view_range")
    
    if not path:
        return ("Missing required parameter: path", True)
    
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        return (f"File or directory {path} does not exist", True)
    
    # If the path is a directory, list its contents
    if file_path.is_dir():
        try:
            # Get all files and directories in the directory
            items = list(file_path.iterdir())
            
            # Sort items (directories first, then files)
            dirs = [item.name + "/" for item in items if item.is_dir()]
            files = [item.name for item in items if item.is_file()]
            
            dirs.sort()
            files.sort()
            
            # Combine the lists
            contents = dirs + files
            
            if not contents:
                return (f"Directory {path} is empty", False)
            
            # Add count information to the output
            dir_count = len(dirs)
            file_count = len(files)
            count_info = f"Total: {len(contents)} ({dir_count} directories, {file_count} files)"
            
            return ("\n".join(contents) + f"\n{count_info}", False)
        except Exception as e:
            return (f"Error listing directory {path}: {str(e)}", True)
    
    # If the path is a file, view its contents
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        # If view_range is specified, return only the specified lines
        if view_range:
            start_line = max(1, view_range[0]) - 1  # Convert to 0-indexed
            end_line = view_range[1] if view_range[1] != -1 else len(content)
            end_line = min(end_line, len(content))
            
            # Adjust content to only include the specified lines
            content = content[start_line:end_line]
            
            # Add line numbers to each line
            numbered_content = []
            for i, line in enumerate(content):
                line_number = start_line + i + 1  # Convert back to 1-indexed
                numbered_content.append(f"{line_number}: {line}")
            
            # Add line count information
            line_count = end_line - start_line
            
            # Show relative path if it's not an absolute path
            display_path = path if os.path.isabs(path) else os.path.relpath(file_path, get_config().workspace_dir)
            line_info = f"Viewed {line_count} lines from {display_path}"
            
            return ("".join(numbered_content) + f"\n{line_info}", False)
        else:
            # Add line numbers to each line
            numbered_content = []
            for i, line in enumerate(content):
                line_number = i + 1  # 1-indexed line numbers
                numbered_content.append(f"{line_number}: {line}")
            
            # Add line count information
            # Show relative path if it's not an absolute path
            display_path = path if os.path.isabs(path) else os.path.relpath(file_path, get_config().workspace_dir)
            line_info = f"Viewed {len(content)} lines from {display_path}"
            
            return ("".join(numbered_content) + f"\n{line_info}", False)
    except Exception as e:
        return (f"Error viewing file {path}: {str(e)}", True)


def handle_str_replace(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Replace a specific string in a file with a new string.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file to modify
            - old_str: The text to replace
            - new_str: The new text to insert
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    old_str = args.get("old_str")
    new_str = args.get("new_str")
    
    if not path:
        return ("Missing required parameter: path", True)
    if old_str is None:
        return ("Missing required parameter: old_str", True)
    if new_str is None:
        return ("Missing required parameter: new_str", True)
    
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        return (f"File {path} does not exist", True)
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup the file before making changes
        backup_file(path, content)
        
        # Save the current content for undo (legacy approach, will be deprecated)
        if path not in _file_history:
            _file_history[path] = []
        _file_history[path].append(content)
        
        # Check if old_str exists in the content
        if old_str not in content:
            return ("Error: No match found for replacement. Please check your text and try again.", True)
        
        # Count occurrences to check for multiple matches
        match_count = content.count(old_str)
        if match_count > 1:
            return (f"Error: Found {match_count} matches for replacement text. Please provide more context to make a unique match.", True)
        
        # Replace the string
        new_content = content.replace(old_str, new_str)
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return (f"Successfully replaced string in file {path}", False)
    except Exception as e:
        return (f"Error replacing string in file {path}: {str(e)}", True)


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
    
    if not path:
        return ("Missing required parameter: path", True)
    if insert_line is None:
        return ("Missing required parameter: insert_line", True)
    if new_str is None:
        return ("Missing required parameter: new_str", True)
    
    # Get the workspace directory from config
    workspace_dir = get_config().workspace_dir
    
    # Make path absolute if it's not already
    if not os.path.isabs(path):
        path = os.path.join(workspace_dir, path)
    
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        return (f"File {path} does not exist", True)
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = "".join(lines)
        
        # Backup the file before making changes
        backup_file(path, content)
        
        # Save the current content for undo (legacy approach, will be deprecated)
        if path not in _file_history:
            _file_history[path] = []
        _file_history[path].append(content)
        
        # Check if insert_line is valid
        if insert_line < 0 or insert_line > len(lines):
            return (f"Invalid insert line {insert_line} for file {path}", True)
        
        # Ensure new_str ends with a newline if it doesn't already
        if new_str and not new_str.endswith('\n'):
            new_str += '\n'
        
        # Insert the new string
        lines.insert(insert_line, new_str)
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return (f"Successfully inserted text at line {insert_line} in file {path}", False)
    except Exception as e:
        return (f"Error inserting text in file {path}: {str(e)}", True)


def handle_undo_edit(args: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Undo the last edit made to a file.
    
    Args:
        args: Dictionary containing:
            - path: Path to the file whose last edit should be undone
        
    Returns:
        A tuple containing (message, is_error)
    """
    path = args.get("path")
    
    if not path:
        return ("Missing required parameter: path", True)
    
    # Get the workspace directory from config
    workspace_dir = get_config().workspace_dir
    
    # Make path absolute if it's not already
    if not os.path.isabs(path):
        path = os.path.join(workspace_dir, path)
    
    # First try to use the file-based backup system
    backup_info = get_backup_info()
    if backup_info:
        backup_path = backup_info['path']
        backup_content = backup_info['content']
        
        # If a path was provided, check if it matches the backup
        if path != backup_path:
            return (f"No backup found for file {path}. Last edited file was {backup_path}", True)
        
        try:
            # Write the backup content back to the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            
            return (f"Successfully undid last edit to file {path}", False)
        except Exception as e:
            return (f"Error undoing edit to file {path}: {str(e)}", True)
    
    # Fall back to the in-memory history if no file backup exists
    if path not in _file_history or not _file_history[path]:
        return (f"No edit history for file {path}", True)
    
    try:
        # Get the last content
        last_content = _file_history[path].pop()
        
        # Write the last content back to the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(last_content)
        
        return (f"Successfully undid last edit to file {path}", False)
    except Exception as e:
        return (f"Error undoing edit to file {path}: {str(e)}", True)
