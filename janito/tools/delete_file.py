"""
Tool for deleting files through the claudine agent.
"""
import os
from pathlib import Path
from typing import Dict, Any, Tuple
from janito.config import get_config
from janito.tools.str_replace_editor.utils import normalize_path
from janito.tools.decorators import tool_meta


@tool_meta(label="Deleting file {file_path}")
def delete_file(
    file_path: str,
) -> Tuple[str, bool]:
    """
    Delete an existing file.
    
    Args:
        file_path: Path to the file to delete, relative to the workspace directory
        
    Returns:
        A tuple containing (message, is_error)
    """
    # Normalize the file path
    path = normalize_path(file_path)
    
    # Convert to Path object for better path handling
    path_obj = Path(path)
    
    # Check if the file exists
    if not path_obj.exists():
        return (f"File {path} does not exist.", True)
    
    # Check if it's a directory
    if path_obj.is_dir():
        return (f"{path} is a directory, not a file. Use delete_directory for directories.", True)
    
    # Delete the file
    try:
        path_obj.unlink()
        return (f"Successfully deleted file {path}", False)
    except Exception as e:
        return (f"Error deleting file {path}: {str(e)}", True)
