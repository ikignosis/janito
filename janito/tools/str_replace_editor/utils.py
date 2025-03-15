"""
Utility functions for the str_replace_editor package.
"""
import os
import pathlib
from typing import Dict, Any, Optional
from janito.config import get_config

def normalize_path(path: str) -> str:
    """
    Normalizes a path relative to the workspace directory.
    
    Args:
        path: The original path
        
    Returns:
        The normalized path relative to the workspace directory
    """
    # If path is absolute, return it as is
    if os.path.isabs(path):
        return path
    
    # Get workspace directory
    workspace_dir = get_config().workspace_dir
    
    # Handle paths starting with ./ by removing the ./ prefix
    if path.startswith('./'):
        path = path[2:]
    
    # Handle paths starting with ../ as relative to the workspace directory
    # This is more complex and might need more sophisticated handling
    
    # Make the path relative to the workspace directory
    return os.path.join(workspace_dir, path)

def backup_file(file_path: str, content: str) -> None:
    """
    Backup a file before editing it.
    
    Args:
        file_path: Path to the file being edited
        content: Current content of the file
    """
    # Get workspace directory
    workspace_dir = get_config().workspace_dir
    
    # Create .janito/undo directory in the workspace if it doesn't exist
    backup_dir = pathlib.Path(workspace_dir) / ".janito" / "undo"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Store the original path
    path_file = backup_dir / "path"
    with open(path_file, 'w', encoding='utf-8') as f:
        f.write(file_path)
    
    # Store the original content
    content_file = backup_dir / "content"
    with open(content_file, 'w', encoding='utf-8') as f:
        f.write(content)

def get_backup_info() -> Optional[Dict[str, str]]:
    """
    Get the backup information for the last edited file.
    
    Returns:
        Dictionary with 'path' and 'content' keys, or None if no backup exists
    """
    # Get workspace directory
    workspace_dir = get_config().workspace_dir
    
    path_file = pathlib.Path(workspace_dir) / ".janito" / "undo" / "path"
    content_file = pathlib.Path(workspace_dir) / ".janito" / "undo" / "content"
    
    if not path_file.exists() or not content_file.exists():
        return None
    
    try:
        with open(path_file, 'r', encoding='utf-8') as f:
            path = f.read()
        
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'path': path,
            'content': content
        }
    except Exception:
        return None

# Store file history for undo operations (in-memory backup, will be deprecated)
_file_history = {}
