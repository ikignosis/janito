import os
import fnmatch
import re
import pathlib
from typing import List, Dict, Any, Tuple
from janito.tools.decorators import tool_meta


@tool_meta(label="Searching for '{text_pattern}' in files matching '{file_pattern}'")
def search_text(text_pattern: str, file_pattern: str = "*", root_dir: str = ".", recursive: bool = True, respect_gitignore: bool = True) -> Tuple[str, bool]:
    """
    Search for text patterns within files matching a filename pattern.
    
    Args:
        text_pattern: Text pattern to search for within files
        file_pattern: Pattern to match file names against (default: "*")
                     Multiple patterns can be specified using semicolons or spaces as separators
                     Examples: "*.py *.toml *.sh *.md test*"
        root_dir: Root directory to start search from (default: current directory)
        recursive: Whether to search recursively in subdirectories (default: True)
        respect_gitignore: Whether to respect .gitignore files (default: True)
        
    Returns:
        A tuple containing (message, is_error)
    """
    try:
        # Convert to absolute path if relative
        abs_root = os.path.abspath(root_dir)
        
        if not os.path.isdir(abs_root):
            return f"Error: Directory '{root_dir}' does not exist", True
        
        # Compile the regex pattern for better performance
        try:
            regex = re.compile(text_pattern)
        except re.error as e:
            return f"Error: Invalid regex pattern '{text_pattern}': {str(e)}", True
        
        matching_files = []
        match_count = 0
        results = []
        
        # Get gitignore patterns if needed
        ignored_patterns = []
        if respect_gitignore:
            ignored_patterns = _get_gitignore_patterns(abs_root)
        
        # Use os.walk for recursive behavior
        if recursive:
            for dirpath, dirnames, filenames in os.walk(abs_root):
                # Skip ignored directories
                if respect_gitignore:
                    dirnames[:] = [d for d in dirnames if not _is_ignored(os.path.join(dirpath, d), ignored_patterns, abs_root)]
                
                # Handle multiple patterns separated by semicolons or spaces
                patterns = []
                if ';' in file_pattern:
                    patterns = file_pattern.split(';')
                elif ' ' in file_pattern:
                    patterns = file_pattern.split()
                else:
                    patterns = [file_pattern]
                
                for pattern in patterns:
                    for filename in fnmatch.filter(filenames, pattern):
                        file_path = os.path.join(dirpath, filename)
                        
                        # Skip ignored files
                        if respect_gitignore and _is_ignored(file_path, ignored_patterns, abs_root):
                            continue
                        
                        # Skip if already processed this file
                        if file_path in matching_files:
                            continue
                        
                        file_matches = _search_file(file_path, regex, abs_root)
                        if file_matches:
                            matching_files.append(file_path)
                            match_count += len(file_matches)
                            results.append(f"\n{os.path.relpath(file_path, abs_root)} ({len(file_matches)} matches):")
                            results.extend(file_matches)
        else:
            # Non-recursive mode - only search in the specified directory
            # Handle multiple patterns separated by semicolons or spaces
            patterns = []
            if ';' in file_pattern:
                patterns = file_pattern.split(';')
            elif ' ' in file_pattern:
                patterns = file_pattern.split()
            else:
                patterns = [file_pattern]
            
            for pattern in patterns:
                for filename in fnmatch.filter(os.listdir(abs_root), pattern):
                    file_path = os.path.join(abs_root, filename)
                    
                    # Skip ignored files
                    if respect_gitignore and _is_ignored(file_path, ignored_patterns, abs_root):
                        continue
                    
                    # Skip if already processed this file
                    if file_path in matching_files:
                        continue
                    
                    if os.path.isfile(file_path):
                        file_matches = _search_file(file_path, regex, abs_root)
                        if file_matches:
                            matching_files.append(file_path)
                            match_count += len(file_matches)
                            results.append(f"\n{os.path.relpath(file_path, abs_root)} ({len(file_matches)} matches):")
                            results.extend(file_matches)
        
        if matching_files:
            result_text = "\n".join(results)
            summary = f"\n{match_count} matches in {len(matching_files)} files"
            return f"Searching for '{text_pattern}' in files matching '{file_pattern}':{result_text}\n{summary}", False
        else:
            return f"No matches found for '{text_pattern}' in files matching '{file_pattern}' in '{root_dir}'", False
            
    except Exception as e:
        return f"Error searching text: {str(e)}", True


def _search_file(file_path: str, pattern: re.Pattern, root_dir: str) -> List[str]:
    """
    Search for regex pattern in a file and return matching lines with line numbers.
    
    Args:
        file_path: Path to the file to search
        pattern: Compiled regex pattern to search for
        root_dir: Root directory (for path display)
        
    Returns:
        List of formatted matches with line numbers and content
    """
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f, 1):
                if pattern.search(line):
                    # Truncate long lines for display
                    display_line = line.strip()
                    if len(display_line) > 100:
                        display_line = display_line[:97] + "..."
                    matches.append(f"  Line {i}: {display_line}")
    except (UnicodeDecodeError, IOError) as e:
        # Skip binary files or files with encoding issues
        pass
    return matches


def _get_gitignore_patterns(root_dir: str) -> List[str]:
    """
    Get patterns from .gitignore files.
    
    Args:
        root_dir: Root directory to start from
        
    Returns:
        List of gitignore patterns
    """
    patterns = []
    
    # Check for .gitignore in the root directory
    gitignore_path = os.path.join(root_dir, '.gitignore')
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception:
            pass
    
    # Add common patterns that are always ignored
    common_patterns = [
        '.git/', '.venv/', 'venv/', '__pycache__/', '*.pyc', 
        '*.pyo', '*.pyd', '.DS_Store', '*.so', '*.egg-info/'
    ]
    patterns.extend(common_patterns)
    
    return patterns


def _is_ignored(path: str, patterns: List[str], root_dir: str) -> bool:
    """
    Check if a path should be ignored based on gitignore patterns.
    
    Args:
        path: Path to check
        patterns: List of gitignore patterns
        root_dir: Root directory for relative paths
        
    Returns:
        True if the path should be ignored, False otherwise
    """
    # Get the relative path from the root directory
    rel_path = os.path.relpath(path, root_dir)
    
    # Convert to forward slashes for consistency with gitignore patterns
    rel_path = rel_path.replace(os.sep, '/')
    
    # Add trailing slash for directories
    if os.path.isdir(path) and not rel_path.endswith('/'):
        rel_path += '/'
    
    for pattern in patterns:
        # Handle negation patterns (those starting with !)
        if pattern.startswith('!'):
            continue  # Skip negation patterns for simplicity
        
        # Handle directory-specific patterns (those ending with /)
        if pattern.endswith('/'):
            if os.path.isdir(path) and fnmatch.fnmatch(rel_path, pattern + '*'):
                return True
        
        # Handle file patterns
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        
        # Handle patterns without wildcards as path prefixes
        if '*' not in pattern and '?' not in pattern and rel_path.startswith(pattern):
            return True
    
    return False