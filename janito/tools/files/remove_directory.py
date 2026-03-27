#!/usr/bin/env python3
"""
Remove Directory Tool - A class-based tool for removing directories.

This tool demonstrates how to use the base tool class with progress reporting.
It provides safe directory removal with options for recursive deletion.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.remove_directory [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import shutil
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="w")
class RemoveDirectory(BaseTool):
    """
    Tool for removing a directory from the filesystem.
    """
    
    def run(self, directory: str, recursive: bool = False, force: bool = False) -> Dict[str, Any]:
        """
        Remove a directory from the filesystem.
        
        Args:
            directory (str): The path to the directory to remove
            recursive (bool): Whether to remove directory and all its contents recursively (default: False)
            force (bool): Whether to ignore errors and continue (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'directory': the directory that was removed
                - 'message': success message with details
                - 'recursive': whether recursive removal was used
                - 'items_removed': number of items removed (if recursive=True)
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_directory = os.path.abspath(directory)
            norm_path_str = norm_path(abs_directory)
            
            # Report start
            recursive_str = "recursively" if recursive else ""
            self.report_start(f"Removing directory {norm_path_str} {recursive_str}", end="")
            
            if not os.path.exists(abs_directory):
                if force:
                    self.report_result(f"Directory does not exist (ignored due to force=True): {norm_path_str}")
                    return {
                        "success": True,
                        "directory": directory,
                        "message": f"Directory does not exist (ignored due to force=True): {norm_path_str}",
                        "recursive": recursive,
                        "force": force,
                        "items_removed": 0
                    }
                else:
                    self.report_error(f"Directory does not exist: {norm_path_str}")
                    return {
                        "success": False,
                        "error": f"Directory does not exist: {norm_path_str}",
                        "directory": directory,
                        "recursive": recursive,
                        "force": force
                    }
            
            if not os.path.isdir(abs_directory):
                if force:
                    self.report_result(f"Path is not a directory (ignored due to force=True): {norm_path_str}")
                    return {
                        "success": True,
                        "directory": directory,
                        "message": f"Path is not a directory (ignored due to force=True): {norm_path_str}",
                        "recursive": recursive,
                        "force": force,
                        "items_removed": 0
                    }
                else:
                    self.report_error(f"Path is not a directory: {norm_path_str}")
                    return {
                        "success": False,
                        "error": f"Path is not a directory: {norm_path_str}",
                        "directory": directory,
                        "recursive": recursive,
                        "force": force
                    }
            
            # Count items if recursive
            items_removed = 0
            if recursive:
                try:
                    # Count items before removal
                    for root, dirs, files in os.walk(abs_directory):
                        items_removed += len(dirs) + len(files)
                    size_str = f"({items_removed} items)"
                    self.report_progress(f" {size_str}", end="")
                    
                    # Remove recursively
                    shutil.rmtree(abs_directory)
                    message = f"Successfully removed directory recursively {norm_path_str}"
                except Exception as e:
                    if force:
                        # Try alternative removal methods or just report and continue
                        self.report_warning(f"Partial removal completed, some items may remain: {str(e)}")
                        message = f"Partially removed directory {norm_path_str} (force mode)"
                    else:
                        raise e
            else:
                # Non-recursive removal (only empty directories)
                try:
                    os.rmdir(abs_directory)
                    message = f"Successfully removed empty directory {norm_path_str}"
                except OSError as e:
                    if e.errno == 39:  # Directory not empty
                        if force:
                            self.report_warning(f"Directory not empty, attempting recursive removal (force mode)")
                            # Count items before removal
                            for root, dirs, files in os.walk(abs_directory):
                                items_removed += len(dirs) + len(files)
                            size_str = f"({items_removed} items)"
                            self.report_progress(f" {size_str}", end="")
                            shutil.rmtree(abs_directory)
                            message = f"Successfully removed directory recursively {norm_path_str} (force mode)"
                        else:
                            self.report_error(f"Directory not empty: {norm_path_str} (use recursive=True to remove non-empty directories)")
                            return {
                                "success": False,
                                "error": f"Directory not empty: {norm_path_str} (use recursive=True to remove non-empty directories)",
                                "directory": directory,
                                "recursive": recursive,
                                "force": force
                            }
                    else:
                        raise e
            
            self.report_result(message)
            
            return {
                "success": True,
                "directory": directory,
                "message": message,
                "recursive": recursive,
                "force": force,
                "items_removed": items_removed
            }
            
        except PermissionError as e:
            self.report_error(f"Permission denied: {str(e)}")
            return {
                "success": False,
                "error": f"Permission denied: {str(e)}",
                "directory": directory,
                "recursive": recursive,
                "force": force
            }
        except OSError as e:
            self.report_error(f"OS Error removing directory: {str(e)}")
            return {
                "success": False,
                "error": f"OS Error removing directory: {str(e)}",
                "directory": directory,
                "recursive": recursive,
                "force": force
            }
        except Exception as e:
            self.report_error(f"Error removing directory: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory,
                "recursive": recursive,
                "force": force
            }


# CLI interface for testing
def main():
    """Command line interface for testing the RemoveDirectoryTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove directory tool for AI function calling")
    parser.add_argument("directory", help="Directory path to remove")
    parser.add_argument("--recursive", "-r", action="store_true", help="Remove directory and all contents recursively")
    parser.add_argument("--force", "-f", action="store_true", help="Force removal, ignore errors")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = RemoveDirectory()
    result = tool_instance.run(
        directory=args.directory,
        recursive=args.recursive,
        force=args.force
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(result["message"])
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
