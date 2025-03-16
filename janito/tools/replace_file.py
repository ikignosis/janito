"""
Replace file tool that overwrites a file with new content.
"""
import os
from typing import Tuple

from janito.tools.decorators import tool


@tool
def replace_file(file_path: str, new_content: str) -> Tuple[str, bool]:
    """
    Replace an existing file with new content.
    
    Args:
        file_path: Path to the file to replace, relative to the workspace directory
        new_content: New content to write to the file
        
    Returns:
        A tuple containing (message, is_error)
    """
    try:
        # Convert relative path to absolute path
        abs_path = os.path.abspath(file_path)
        
        # Check if file exists
        if not os.path.isfile(abs_path):
            return f"Error: File '{file_path}' does not exist", True
            
        # Write new content to the file
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Successfully replaced file '{file_path}'", False
    except Exception as e:
        return f"Error replacing file '{file_path}': {str(e)}", True