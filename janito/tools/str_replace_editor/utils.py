"""
Utility functions for the str_replace_editor package.
"""
import os
from janito.config import get_config

def normalize_path(path: str) -> str:
    """
    Normalizes a path relative to the workspace directory.
    
    For internal operations, converts relative paths to absolute paths
    based on the workspace directory.
    
    Args:
        path: The original path
        
    Returns:
        The normalized absolute path
    """
    # If path is absolute, return it as is
    if os.path.isabs(path):
        return path
    
    # Handle paths starting with ./ by removing the ./ prefix
    if path.startswith('./'):
        path = path[2:]
    
    # Convert relative paths to absolute paths for internal operations
    workspace_dir = get_config().workspace_dir
    return os.path.normpath(os.path.join(workspace_dir, path))

# Store file history for undo operations (in-memory backup)
_file_history = {}
