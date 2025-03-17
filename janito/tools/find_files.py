import os
import glob
import fnmatch  # Still needed for gitignore pattern matching
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
            
            # Check if the search pattern itself is in the gitignore
            if _is_pattern_ignored(pattern, ignored_patterns):
                warning_msg = f"Warning: The search pattern '{pattern}' matches patterns in .gitignore. Search may not yield expected results."
                print_error(warning_msg, "Gitignore Conflict")
                return warning_msg, True
        
        # Use glob for pattern matching
        # Construct the glob pattern with the root directory
        glob_pattern = os.path.join(abs_root, pattern) if not pattern.startswith(os.path.sep) else pattern
        
        # Use recursive glob if needed
        if recursive:
            # Use ** pattern for recursive search if not already in the pattern
            if '**' not in glob_pattern:
                # Check if the pattern already has a directory component
                if os.path.sep in pattern or '/' in pattern:
                    # Pattern already has directory component, keep as is
                    pass
                else:
                    # Add ** to search in all subdirectories
                    glob_pattern = os.path.join(abs_root, '**', pattern)
            
            # Use recursive=True for Python 3.5+ glob
            glob_files = glob.glob(glob_pattern, recursive=True)
        else:
            # Non-recursive mode - only search in the specified directory
            glob_files = glob.glob(glob_pattern)
        
        # Process the glob results
        for file_path in glob_files:
            # Skip directories
            if not os.path.isfile(file_path):
                continue
                
            # Skip ignored files
            if respect_gitignore and _is_ignored(file_path, ignored_patterns, abs_root):
                continue
            
            # Convert to relative path from root_dir
            rel_path = os.path.relpath(file_path, abs_root)
            matching_files.append(rel_path)
        
        # Sort the files for consistent output
        matching_files.sort()
        
        if matching_files:
            file_list = "\n- ".join(matching_files)
            result_msg = f"Found {len(matching_files)} files matching pattern '{pattern}':\n- {file_list}"
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


def _is_pattern_ignored(search_pattern: str, gitignore_patterns: List[str]) -> bool:
    """
    Check if a search pattern conflicts with gitignore patterns.
    
    Args:
        search_pattern: The search pattern to check
        gitignore_patterns: List of gitignore patterns
        
    Returns:
        True if the search pattern conflicts with gitignore patterns, False otherwise
    """
    # Remove any directory part from the search pattern
    pattern_only = search_pattern.split('/')[-1]
    
    for git_pattern in gitignore_patterns:
        # Skip negation patterns
        if git_pattern.startswith('!'):
            continue
            
        # Remove trailing slash for directory patterns
        if git_pattern.endswith('/'):
            git_pattern = git_pattern[:-1]
            
        # Direct match
        if git_pattern == search_pattern or git_pattern == pattern_only:
            return True
            
        # Check if the gitignore pattern is a prefix of the search pattern
        if search_pattern.startswith(git_pattern) and (
            len(git_pattern) == len(search_pattern) or 
            search_pattern[len(git_pattern)] in ['/', '\\']
        ):
            return True
            
        # Check for wildcard matches
        if '*' in git_pattern or '?' in git_pattern:
            # Check if the search pattern would be caught by this gitignore pattern
            if fnmatch.fnmatch(search_pattern, git_pattern) or fnmatch.fnmatch(pattern_only, git_pattern):
                return True
                
    return False


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