"""
Handler for the create command in str_replace_editor.
"""
import os
import pathlib
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.rich_console import print_info, print_success, print_error
from janito.tools.usage_tracker import get_tracker
from ..utils import normalize_path

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
    
    # Count the number of lines in the file content
    line_count = len(file_text.splitlines())
    print_info(f"Creating file: {path} (+{line_count} lines)", "File Creation")
    
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