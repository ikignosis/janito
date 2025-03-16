import os
import fnmatch
from typing import List, Tuple
from janito.tools.rich_console import print_info, print_success, print_error


def find_files(pattern: str, root_dir: str = ".", recursive: bool = True, respect_gitignore: bool = True) -> Tuple[str, bool]:
    """
    Find files whose path matches a glob pattern.
    
    Args:
        pattern: pattern to match file paths against (e.g., "*.py", "*/tools/*.py")
        root_dir: root directory to start search from (default: current directory)
        recursive: Whether to search recursively in subdirectories (default: True)
        respect_gitignore: Whether to respect .gitignore files (default: True)
        
    Returns:
        A tuple containing (message, is_error)
    """
    print_info(
        f"Finding files matching path pattern {pattern}, on {root_dir} " +
        f"({'recursive' if recursive else 'non-recursive'}, " +
        f"{'respecting gitignore' if respect_gitignore else 'ignoring gitignore'})",
        "File Search"
    )
    try:
        # Convert to absolute path if relative
        abs_root = os.path.abspath(root_dir)
        
        if not os.path.isdir(abs_root):
            error_msg = f"Error: Directory '{root_dir}' does not exist"
            print_error(error_msg, "Directory Error")
            return error_msg, True
        
        matching_files = []
        
        # Get gitignore patterns if needed
        ignored_patterns = []
        if respect_gitignore:
            ignored_patterns = _get_gitignore_patterns(abs_root)
        
        # Use os.walk for more intuitive recursive behavior
        if recursive:
            for dirpath, dirnames, filenames in os.walk(abs_root):
                # Skip ignored directories
                if respect_gitignore:
                    dirnames[:] = [d for d in dirnames if not _is_ignored(os.path.join(dirpath, d), ignored_patterns, abs_root)]
                
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    
                    # Skip ignored files
                    if respect_gitignore and _is_ignored(file_path, ignored_patterns, abs_root):
                        continue
                    
                    # Convert to relative path from root_dir
                    rel_path = os.path.relpath(file_path, abs_root)
                    # Match against the relative path, not just the filename
                    if fnmatch.fnmatch(rel_path, pattern):
                        matching_files.append(rel_path)
        else:
            # Non-recursive mode - only search in the specified directory
            for filename in os.listdir(abs_root):
                file_path = os.path.join(abs_root, filename)
                
                # Skip ignored files
                if respect_gitignore and _is_ignored(file_path, ignored_patterns, abs_root):
                    continue
                
                if os.path.isfile(file_path):
                    # Convert to relative path from root_dir
                    rel_path = os.path.relpath(file_path, abs_root)
                    # Match against the relative path, not just the filename
                    if fnmatch.fnmatch(rel_path, pattern):
                        matching_files.append(rel_path)
        
        # Sort the files for consistent output
        matching_files.sort()
        
        if matching_files:
            file_list = "\n- ".join(matching_files)
            result_msg = f"Found {len(matching_files)} files matching pattern '{pattern}':\n- {file_list}\n{len(matching_files)}"
            print_success(result_msg, "Search Results")
            return result_msg, False
        else:
            result_msg = f"No files found matching pattern '{pattern}' in '{root_dir}'"
            print_info(result_msg, "Search Results")
            return result_msg, False
            
    except Exception as e:
        error_msg = f"Error finding files: {str(e)}"
        print_error(error_msg, "Search Error")
        return error_msg, True


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