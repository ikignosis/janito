"""
Path utility functions for normalizing paths relative to the current working directory.
"""

import os
from pathlib import Path


def norm_path(path):
    """
    Normalize a path relative to the current working directory.
    
    - If the path matches exactly the current working directory, return the full path.
    - If the path is a subpath of the working directory, return './relative_path'.
    - Otherwise, return the original path unchanged.
    
    Args:
        path (str or Path): The path to normalize.
        
    Returns:
        str: The normalized path.
    """
    # Convert to Path object if it's a string
    if isinstance(path, str):
        path_obj = Path(path)
    else:
        path_obj = path
    
    # Get absolute paths
    abs_path = path_obj.resolve()
    cwd = Path.cwd().resolve()
    
    # If the path matches exactly the current working directory
    if abs_path == cwd:
        return str(abs_path)
    
    # If the path is a subpath of the working directory
    try:
        # Try to get the relative path
        rel_path = abs_path.relative_to(cwd)
        # If we get here, it's a subpath
        # Convert to POSIX style (forward slashes) for consistent output
        return f"./{rel_path.as_posix()}"
    except ValueError:
        # If relative_to raises ValueError, it's not a subpath
        return str(path_obj)