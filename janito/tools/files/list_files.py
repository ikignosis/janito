#!/usr/bin/env python3
"""
List Files Tool - A class-based tool for listing files and directories.

This tool can be injected into AI clients to allow them to explore file systems.
It provides the ability to list files in a directory, with optional filtering by pattern.

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
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List files and directories in the specified path.
        
        Args:
            directory (str): The directory path to list. Default is current directory (".").
            pattern (str, optional): File pattern to filter results (e.g., "*.py", "data_*.csv").
            recursive (bool): Whether to list files recursively. Default is False.
            max_depth (int, optional): Maximum depth for recursive listing. Default is None (unlimited).
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'files': list of file/directory paths
                - 'directory': the directory that was listed
                - 'pattern': the pattern used for filtering (if any)
                - 'recursive': whether recursive listing was used
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
                    "recursive": recursive
                }
            
            if not os.path.isdir(abs_directory):
                self.report_error(f"Path is not a directory: {norm_dir}")
                return {
                    "success": False,
                    "error": f"Path is not a directory: {norm_dir}",
                    "directory": directory,
                    "pattern": pattern,
                    "recursive": recursive
                }
            
            # Report start of operation
            recursive_str = "recursively" if recursive else ""
            self.report_start(f"📁 Listing files at {norm_dir} {recursive_str}", end="")
            
            files = []
            dir_count = 0
            file_count = 0
            
            if recursive:
                if max_depth is None:
                    for root, dirs, filenames in os.walk(abs_directory):
                        dir_count += len(dirs)
                        file_count += len(filenames)
                        for name in dirs + filenames:
                            full_path = os.path.join(root, name)
                            rel_path = os.path.relpath(full_path, abs_directory)
                            if pattern is None or _matches_pattern(name, pattern):
                                files.append(rel_path if rel_path != "." else name)
                else:
                    # Walk with depth limit
                    for root, dirs, filenames in os.walk(abs_directory):
                        depth = root[len(abs_directory):].count(os.sep)
                        if depth <= max_depth:
                            dir_count += len(dirs)
                            file_count += len(filenames)
                            for name in dirs + filenames:
                                full_path = os.path.join(root, name)
                                rel_path = os.path.relpath(full_path, abs_directory)
                                if pattern is None or _matches_pattern(name, pattern):
                                    files.append(rel_path if rel_path != "." else name)
                        else:
                            dirs[:] = []  # Don't recurse further
            else:
                # Non-recursive listing
                items = os.listdir(abs_directory)
                for item in items:
                    item_path = os.path.join(abs_directory, item)
                    if os.path.isdir(item_path):
                        dir_count += 1
                    else:
                        file_count += 1
                    if pattern is None or _matches_pattern(item, pattern):
                        files.append(item)
            
            # Sort files for consistent output
            files.sort()
            
            # Report results
            total_found = len(files)
            self.report_result(f"Found {total_found} items ({file_count} files, {dir_count} dirs)")
            
            return {
                "success": True,
                "files": files,
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "max_depth": max_depth,
                "stats": {
                    "total_items": total_found,
                    "files": file_count,
                    "directories": dir_count
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
                "max_depth": max_depth
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
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = ListFiles()
    result = tool_instance.run(
        directory=args.directory,
        pattern=args.pattern,
        recursive=args.recursive,
        max_depth=args.max_depth
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
            print("-" * 40)
            for file in result["files"]:
                print(file)
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
