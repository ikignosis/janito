#!/usr/bin/env python3
"""
List Files Tool - A class-based tool for listing files and directories.

This tool can be injected into AI clients to allow them to explore file systems.
It provides the ability to list files in a directory, with optional filtering by pattern.
Optionally respects .gitignore patterns when enabled.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.list_files [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, List, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


def _matches_pattern(filename: str, pattern: str) -> bool:
    """
    Check if filename matches the given pattern using Unix shell-style wildcards.
    
    Args:
        filename (str): The filename to check
        pattern (str): The pattern to match against (e.g., "*.py", "data_??.csv")
    
    Returns:
        bool: True if filename matches pattern, False otherwise
    """
    import fnmatch
    return fnmatch.fnmatch(filename, pattern)


def _load_gitignore_spec(directory: str):
    """
    Load .gitignore patterns from the specified directory.
    
    Uses the 'pathspec' library for proper gitignore parsing.
    
    Args:
        directory (str): The directory to look for .gitignore
        
    Returns:
        A PathSpec object, or None if no .gitignore file exists.
        
    Raises:
        ImportError: If pathspec is not installed.
    """
    gitignore_path = os.path.join(directory, ".gitignore")
    
    if not os.path.exists(gitignore_path):
        return None
    
    try:
        from pathspec import PathSpec
        from pathspec.patterns import GitWildMatchPattern
    except ImportError:
        raise ImportError(
            "The 'pathspec' package is required for .gitignore support. "
            "Install it with: pip install pathspec"
        )
    
    with open(gitignore_path, "r") as f:
        patterns = f.readlines()
    
    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def _is_ignored_by_gitignore(rel_path: str, gitignore_spec) -> bool:
    """
    Check if a path is ignored by gitignore patterns.
    
    Args:
        rel_path (str): Relative path to check
        gitignore_spec: The PathSpec object
        
    Returns:
        bool: True if the path should be ignored
    """
    if gitignore_spec is None:
        return False
    
    # Normalize path separators for matching
    normalized_path = rel_path.replace(os.sep, "/")
    
    return gitignore_spec.match_file(normalized_path)


@tool(permissions="r")
class ListFiles(BaseTool):
    """
    Tool for listing files and directories in the specified path.
    """
    
    def run(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
        recursive: bool = False,
        max_depth: Optional[int] = None,
        respect_gitignore: bool = True
    ) -> Dict[str, Any]:
        """
        List files and directories in the specified path.
        
        Args:
            directory (str): The directory path to list. Default is current directory (".").
            pattern (str, optional): File pattern to filter results (e.g., "*.py", "data_*.csv").
            recursive (bool): Whether to list files recursively. Default is False.
            max_depth (int, optional): Maximum depth for recursive listing. Default is None (unlimited).
            respect_gitignore (bool): Whether to respect .gitignore patterns. Default is True.
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'files': list of file/directory paths
                - 'directory': the directory that was listed
                - 'pattern': the pattern used for filtering (if any)
                - 'recursive': whether recursive listing was used
                - 'respect_gitignore': whether .gitignore was respected
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            # Resolve the directory path
            abs_directory = os.path.abspath(directory)
            
            norm_dir = norm_path(abs_directory)
            
            if not os.path.exists(abs_directory):
                self.report_error(f"Directory does not exist: {norm_dir}")
                return {
                    "success": False,
                    "error": f"Directory does not exist: {norm_dir}",
                    "directory": directory,
                    "pattern": pattern,
                    "recursive": recursive,
                    "respect_gitignore": respect_gitignore
                }
            
            if not os.path.isdir(abs_directory):
                self.report_error(f"Path is not a directory: {norm_dir}")
                return {
                    "success": False,
                    "error": f"Path is not a directory: {norm_dir}",
                    "directory": directory,
                    "pattern": pattern,
                    "recursive": recursive,
                    "respect_gitignore": respect_gitignore
                }
            
            # Load .gitignore if enabled
            gitignore_spec = None
            if respect_gitignore:
                gitignore_spec = _load_gitignore_spec(abs_directory)
            
            # Report start of operation
            gitignore_str = " (respecting .gitignore)" if gitignore_spec else ""
            recursive_str = "recursively" if recursive else ""
            self.report_start(f"📁 Listing files at {norm_dir} {recursive_str}{gitignore_str}", end="")
            
            files = []
            dir_count = 0
            file_count = 0
            gitignore_ignored = 0
            
            if recursive:
                if max_depth is None:
                    for root, dirs, filenames in os.walk(abs_directory):
                        # Filter out ignored directories (modify in-place to prevent walking into them)
                        if gitignore_spec:
                            rel_root = os.path.relpath(root, abs_directory)
                            dirs[:] = [
                                d for d in dirs
                                if not _is_ignored_by_gitignore(
                                    os.path.join(rel_root, d) if rel_root != "." else d,
                                    gitignore_spec
                                )
                            ]
                        
                        dir_count += len(dirs)
                        file_count += len(filenames)
                        
                        for name in dirs + filenames:
                            full_path = os.path.join(root, name)
                            rel_path = os.path.relpath(full_path, abs_directory)
                            is_dir = os.path.isdir(full_path)
                            
                            # Skip if ignored by .gitignore
                            if gitignore_spec and _is_ignored_by_gitignore(rel_path, gitignore_spec):
                                gitignore_ignored += 1
                                continue
                            
                            if pattern is None or _matches_pattern(name, pattern):
                                files.append(rel_path if rel_path != "." else name)
                else:
                    # Walk with depth limit
                    for root, dirs, filenames in os.walk(abs_directory):
                        depth = root[len(abs_directory):].count(os.sep)
                        if depth <= max_depth:
                            # Filter out ignored directories
                            if gitignore_spec:
                                rel_root = os.path.relpath(root, abs_directory)
                                dirs[:] = [
                                    d for d in dirs
                                    if not _is_ignored_by_gitignore(
                                        os.path.join(rel_root, d) if rel_root != "." else d,
                                        gitignore_spec
                                    )
                                ]
                            
                            dir_count += len(dirs)
                            file_count += len(filenames)
                            
                            for name in dirs + filenames:
                                full_path = os.path.join(root, name)
                                rel_path = os.path.relpath(full_path, abs_directory)
                                is_dir = os.path.isdir(full_path)
                                
                                # Skip if ignored by .gitignore
                                if gitignore_spec and _is_ignored_by_gitignore(rel_path, gitignore_spec):
                                    gitignore_ignored += 1
                                    continue
                                
                                if pattern is None or _matches_pattern(name, pattern):
                                    files.append(rel_path if rel_path != "." else name)
                        else:
                            dirs[:] = []  # Don't recurse further
            else:
                # Non-recursive listing
                items = os.listdir(abs_directory)
                for item in items:
                    item_path = os.path.join(abs_directory, item)
                    is_dir = os.path.isdir(item_path)
                    
                    # Skip if ignored by .gitignore
                    if gitignore_spec and _is_ignored_by_gitignore(item, gitignore_spec):
                        gitignore_ignored += 1
                        continue
                    
                    if is_dir:
                        dir_count += 1
                    else:
                        file_count += 1
                    if pattern is None or _matches_pattern(item, pattern):
                        files.append(item)
            
            # Sort files for consistent output
            files.sort()
            
            # Report results
            total_found = len(files)
            gitignore_msg = f", {gitignore_ignored} ignored by .gitignore" if gitignore_ignored else ""
            self.report_result(f"Found {total_found} items ({file_count} files, {dir_count} dirs){gitignore_msg}")
            
            return {
                "success": True,
                "files": files,
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "max_depth": max_depth,
                "respect_gitignore": respect_gitignore,
                "gitignore_applied": gitignore_spec is not None,
                "stats": {
                    "total_items": total_found,
                    "files": file_count,
                    "directories": dir_count,
                    "gitignore_ignored": gitignore_ignored
                }
            }
            
        except Exception as e:
            self.report_error(f"Error during file listing: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "max_depth": max_depth,
                "respect_gitignore": respect_gitignore
            }


# CLI interface for testing
def main():
    """Command line interface for testing the ListFilesTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="List files tool for AI function calling")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to list (default: current directory)")
    parser.add_argument("--pattern", "-p", help="File pattern to filter results (e.g., '*.py')")
    parser.add_argument("--recursive", "-r", action="store_true", help="List files recursively")
    parser.add_argument("--max-depth", "-d", type=int, help="Maximum depth for recursive listing")
    parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore filtering")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = ListFiles()
    result = tool_instance.run(
        directory=args.directory,
        pattern=args.pattern,
        recursive=args.recursive,
        max_depth=args.max_depth,
        respect_gitignore=not args.no_gitignore
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_dir = norm_path(result['directory'])
            print(f"Files in '{norm_dir}':")
            if result["pattern"]:
                print(f"Pattern: {result['pattern']}")
            if result["recursive"]:
                print("Recursive listing enabled")
                if result.get("max_depth"):
                    print(f"Max depth: {result['max_depth']}")
            if result.get("gitignore_applied"):
                print("Respecting .gitignore")
            print("-" * 40)
            for file in result["files"]:
                print(file)
            stats = result.get("stats", {})
            if stats.get("gitignore_ignored", 0) > 0:
                print("-" * 40)
                print(f"(.gitignore filtered {stats['gitignore_ignored']} items)")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
