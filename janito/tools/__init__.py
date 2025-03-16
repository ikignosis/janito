"""
Janito tools package.
"""

from .str_replace_editor import str_replace_editor
from .find_files import find_files
from .delete_file import delete_file
from .search_text import search_text
from .replace_file import replace_file
from .prompt_user import prompt_user

__all__ = ["str_replace_editor", "find_files", "delete_file", "search_text", "replace_file", "prompt_user", "get_tools"]

def get_tools():
    """
    Get a list of all available tools.
    
    Returns:
        List of tool functions (excluding str_replace_editor which is passed separately)
    """
    return [find_files, delete_file, search_text, replace_file, prompt_user]
