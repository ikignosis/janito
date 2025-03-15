"""
Tool for creating files through the claudine agent.
"""
import os
from pathlib import Path
from typing import Dict, Any
from janito.config import get_config


def create_file(
    file_path: str,
    content: str = "",
) -> Dict[str, Any]:
    """
    Create a new file with the given content.
    
    Args:
        file_path: Path to the file to create, relative to the workspace directory
        content: Content to write to the file
        
    Returns:
        Dict with success status and message
    """
    # Get the workspace directory from config
    workspace_dir = get_config().workspace_dir
    
    # Make file_path absolute if it's not already
    if not os.path.isabs(file_path):
        file_path = os.path.join(workspace_dir, file_path)
    
    # Convert to Path object for better path handling
    path = Path(file_path)
    
    # Check if the file already exists
    if path.exists():
        return {"success": False, "message": f"File {file_path} already exists."}
    
    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the content to the file
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "message": f"Successfully created file {file_path}"}
    except Exception as e:
        return {"success": False, "message": f"Error creating file {file_path}: {str(e)}"}
