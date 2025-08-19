"""
File Manager Plugin

Core file and directory operations for managing project files.
"""

from typing import List, Optional
import os


def create_file(path: str, content: str = "", overwrite: bool = False) -> str:
    """Create a new file with content"""
    return f"create_file(path='{path}', content='{len(content)} chars', overwrite={overwrite})"


def read_files(paths: List[str]) -> str:
    """Read multiple files at once"""
    return f"read_files(paths={paths})"


def view_file(
    path: str, from_line: Optional[int] = None, to_line: Optional[int] = None
) -> str:
    """Read specific lines or entire files"""
    range_str = f"{from_line}-{to_line}" if from_line or to_line else "all"
    return f"view_file(path='{path}', range='{range_str}')"


def replace_text_in_file(
    path: str, search_text: str, replacement_text: str, replace_all: bool = True
) -> str:
    """Find and replace text in files"""
    return f"replace_text_in_file(path='{path}', search='{search_text[:20]}...', replace='{replacement_text[:20]}...')"


def validate_file_syntax(path: str) -> str:
    """Check file syntax (Python/Markdown)"""
    return f"validate_file_syntax(path='{path}')"


def create_directory(path: str) -> str:
    """Create new directories"""
    return f"create_directory(path='{path}')"


def remove_directory(path: str, recursive: bool = False) -> str:
    """Remove directories (recursive option)"""
    return f"remove_directory(path='{path}', recursive={recursive})"


def remove_file(path: str) -> str:
    """Delete single files"""
    return f"remove_file(path='{path}')"


def copy_file(sources: str, target: str, overwrite: bool = False) -> str:
    """Copy files or directories"""
    return f"copy_file(sources='{sources}', target='{target}', overwrite={overwrite})"


def move_file(src_path: str, dest_path: str, overwrite: bool = False) -> str:
    """Move/rename files or directories"""
    return f"move_file(src='{src_path}', dest='{dest_path}', overwrite={overwrite})"


def find_files(
    paths: str,
    pattern: str,
    max_depth: Optional[int] = None,
    include_gitignored: bool = False,
) -> str:
    """Search for files by pattern (respects .gitignore)"""
    return f"find_files(paths='{paths}', pattern='{pattern}', max_depth={max_depth})"


# Plugin metadata
__plugin_name__ = "core.filemanager"
__plugin_description__ = "Core file and directory operations"
__plugin_tools__ = [
    create_file,
    read_files,
    view_file,
    replace_text_in_file,
    validate_file_syntax,
    create_directory,
    remove_directory,
    remove_file,
    copy_file,
    move_file,
    find_files,
]
