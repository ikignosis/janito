"""
Command handlers for the str_replace_editor package.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.rich_console import print_info, print_success, print_error, print_warning
from janito.tools.usage_tracker import get_tracker, count_lines_in_string
from .utils import normalize_path, _file_history

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
    
    print_info(f"Creating file: {path}", "File Creation")
    
    if not path:
        return ("Missing required parameter: path", True)
    
    path = normalize_path(path)
    
    # Convert to Path object for better path handling
    file_path = pathlib.Path(path)
    
    # Check if the file already exists - according to spec, create cannot be used if file exists
    if file_path.exists() and file_path.is_file():
        print_error(f"File {path} already exists. The 'create' command cannot be used if the specified path already exists as a file.", "Error")
        return (f"File {path} already exists. The 'create' command cannot be used if the specified path already exists as a file.", True)
    
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the content to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_text)
        # Track file creation
        get_tracker().increment('files_created')
        # Show relative path if it's not an absolute path
        display_path = path if os.path.isabs(path) else os.path.relpath(file_path, get_config().workspace_dir)
        print_success(f"Successfully created file {display_path}", "Success")
        return (f"Successfully created file {display_path}", False)
    except Exception as e:
        print_error(f"Error creating file {path}: {str(e)}", "Error")
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
    
    # First normalize the path to check if it's a file or directory
    normalized_path = normalize_path(path)
    file_path = pathlib.Path(normalized_path)
    
    if file_path.exists():
        if file_path.is_dir():
            print_info(f"Viewing directory: {path}", "Directory View")
        else:
            if view_range:
                print_info(f"Viewing file: {path}, from line {view_range[0]} to {view_range[1]}", "File View")
            else:
                print_info(f"Viewing file: {path}, all lines", "File View")
    else:
        # If path doesn't exist yet, assume it's a file (will be validated later)
        if view_range:
            print_info(f"Viewing file: {path}, from line {view_range[0]} to {view_range[1]}", "File View")
        else:
            print_info(f"Viewing file: {path}, all lines", "File View")
    
    if not path:
        print_error("Missing required parameter: path", "Error")
        return ("Missing required parameter: path", True)
    
    path = normalize_path(path)
    file_path = pathlib.Path(path)
    
    if not file_path.exists():
        print_error(f"File or directory {path} does not exist", "Error")
        return (f"File or directory {path} does not exist", True)
    
    # If the path is a directory, list non-hidden files and directories up to 2 levels deep
    if file_path.is_dir():
        try:
            result = []
            # Process the first level
            for item in sorted(file_path.iterdir()):
                if item.name.startswith('.'):
                    continue  # Skip hidden files/directories
                
                if item.is_dir():
                    result.append(f"{item.name}/")
                    # Process the second level
                    try:
                        for subitem in sorted(item.iterdir()):
                            if subitem.name.startswith('.'):
                                continue  # Skip hidden files/directories
                                
                            if subitem.is_dir():
                                result.append(f"{item.name}/{subitem.name}/")
                            else:
                                result.append(f"{item.name}/{subitem.name}")
                    except PermissionError:
                        # Skip directories we can't access
                        pass
                else:
                    result.append(item.name)
            
            if not result:
                return (f"Directory {path} is empty or contains only hidden files", False)
            
            # Track directory view
            get_tracker().increment('file_views')
            
            # Determine if we need to truncate the output
            MAX_LINES = 100  # Arbitrary limit for demonstration
            output = "\n".join(result)
            if len(result) > MAX_LINES:
                truncated_output = "\n".join(result[:MAX_LINES])
                return (truncated_output + "\n<response clipped>", False)
            
            return (output, False)
        except Exception as e:
            return (f"Error listing directory {path}: {str(e)}", True)
    
    # If the path is a file, view its contents with cat -n style output
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
            
            # Track partial file view
            get_tracker().increment('partial_file_views')
        else:
            # Track full file view
            get_tracker().increment('file_views')
        
        # Add line numbers to each line (cat -n style)
        numbered_content = []
        start_idx = 1 if view_range is None else view_range[0]
        for i, line in enumerate(content):
            line_number = start_idx + i
            # Ensure line ends with newline
            if not line.endswith('\n'):
                line += '\n'
            numbered_content.append(f"{line_number:6d}\t{line}")
        
        # Check if we need to truncate the output
        MAX_LINES = 500  # Arbitrary limit for demonstration
        if len(numbered_content) > MAX_LINES:
            truncated_content = "".join(numbered_content[:MAX_LINES])
            return (truncated_content + "\n<response clipped>", False)
        
        return ("".join(numbered_content), False)
    except Exception as e:
        return (f"Error viewing file {path}: {str(e)}", True)


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
    
    print_info(f"Replacing text in file: {path}", "String Replace Operation")
    
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
        
        # Track the number of lines replaced
        lines_changed = count_lines_in_string(old_str, new_str)
        get_tracker().increment('lines_replaced', lines_changed)
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Show relative path if it's not an absolute path in the original input
        display_path = args.get("path") if os.path.isabs(args.get("path")) else os.path.relpath(file_path, get_config().workspace_dir)
        print_success(f"Successfully replaced string in file {display_path}", "Success")
        return (f"Successfully replaced string in file {display_path}", False)
    except Exception as e:
        # Show relative path if it's not an absolute path in the original input
        display_path = args.get("path") if os.path.isabs(args.get("path")) else os.path.relpath(file_path, get_config().workspace_dir)
        print_error(f"Error replacing string in file {display_path}: {str(e)}", "Error")
        return (f"Error replacing string in file {display_path}: {str(e)}", True)


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
    
    print_info(f"Inserting text in file: {path}, after line {insert_line}", "Insert Operation")
    
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
        print_warning(f"No edit history for file {path}", "Warning")
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
