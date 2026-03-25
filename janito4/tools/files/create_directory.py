#!/usr/bin/env python3
"""
Create Directory Tool - A class-based tool for creating directories.

This tool demonstrates how to use the base tool class with progress reporting.
It provides directory creation with optional parent directory creation.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito4.tools.files.create_directory [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="w")
class CreateDirectory(BaseTool):
    """
    Tool for creating a new directory.
    """
    
    def run(self, directory: str, parents: bool = False, exist_ok: bool = False) -> Dict[str, Any]:
        """
        Create a new directory.
        
        Args:
            directory (str): The path where the directory should be created
            parents (bool): Whether to create parent directories if they don't exist (default: False)
            exist_ok (bool): Whether to ignore errors if directory already exists (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'directory': the directory that was created
                - 'message': success message with details
                - 'created': bool indicating if directory was actually created (vs already existed)
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_directory = os.path.abspath(directory)
            norm_path_str = norm_path(abs_directory)
            
            # Report start
            self.report_start(f"Creating directory {norm_path_str}", end="")
            
            # Check if directory already exists
            if os.path.exists(abs_directory):
                if exist_ok:
                    self.report_result(f"Directory already exists: {norm_path_str}")
                    return {
                        "success": True,
                        "directory": directory,
                        "message": f"Directory already exists: {norm_path_str}",
                        "created": False,
                        "parents": parents,
                        "exist_ok": exist_ok
                    }
                else:
                    self.report_error(f"Directory already exists: {norm_path_str} (use exist_ok=True to ignore)")
                    return {
                        "success": False,
                        "error": f"Directory already exists: {norm_path_str} (use exist_ok=True to ignore)",
                        "directory": directory,
                        "parents": parents,
                        "exist_ok": exist_ok
                    }
            
            # Check if path is a file
            if os.path.isfile(abs_directory):
                self.report_error(f"Path is a file, not a directory: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"Path is a file, not a directory: {norm_path_str}",
                    "directory": directory,
                    "parents": parents,
                    "exist_ok": exist_ok
                }
            
            # Create the directory
            if parents:
                os.makedirs(abs_directory, exist_ok=exist_ok)
                self.report_progress(" (with parents)", end="")
            else:
                os.mkdir(abs_directory)
            
            self.report_result(f"Successfully created directory")
            
            return {
                "success": True,
                "directory": directory,
                "message": f"Successfully created directory {norm_path_str}",
                "created": True,
                "parents": parents,
                "exist_ok": exist_ok
            }
            
        except PermissionError as e:
            self.report_error(f"Permission denied: {str(e)}")
            return {
                "success": False,
                "error": f"Permission denied: {str(e)}",
                "directory": directory,
                "parents": parents,
                "exist_ok": exist_ok
            }
        except OSError as e:
            self.report_error(f"OS Error creating directory: {str(e)}")
            return {
                "success": False,
                "error": f"OS Error creating directory: {str(e)}",
                "directory": directory,
                "parents": parents,
                "exist_ok": exist_ok
            }
        except Exception as e:
            self.report_error(f"Error creating directory: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory,
                "parents": parents,
                "exist_ok": exist_ok
            }


# CLI interface for testing
def main():
    """Command line interface for testing the CreateDirectoryTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create directory tool for AI function calling")
    parser.add_argument("directory", help="Directory path to create")
    parser.add_argument("--parents", "-p", action="store_true", help="Create parent directories as needed")
    parser.add_argument("--exist-ok", "-e", action="store_true", help="Don't raise error if directory already exists")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = CreateDirectory()
    result = tool_instance.run(
        directory=args.directory,
        parents=args.parents,
        exist_ok=args.exist_ok
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