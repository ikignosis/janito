#!/usr/bin/env python3
"""
Delete File Tool - A class-based tool for deleting files.

This tool demonstrates how to use the base tool class with progress reporting.
It provides safe file deletion with confirmation and error handling.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.delete_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="w")
class DeleteFile(BaseTool):
    """
    Tool for deleting a file from the filesystem.
    """
    
    def run(self, filepath: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete a file from the filesystem.
        
        Args:
            filepath (str): The path to the file to delete
            force (bool): Whether to force deletion without checking if it's a file (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'filepath': the file that was deleted
                - 'message': success message with details
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_filepath = os.path.abspath(filepath)
            norm_path_str = norm_path(abs_filepath)
            
            # Report start
            self.report_start(f"Deleting file {norm_path_str}", end="")
            
            if not os.path.exists(abs_filepath):
                self.report_error(f"File does not exist: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"File does not exist: {norm_path_str}",
                    "filepath": filepath
                }
            
            if not force and not os.path.isfile(abs_filepath):
                self.report_error(f"Path is not a file: {norm_path_str} (use force=True to delete directories)")
                return {
                    "success": False,
                    "error": f"Path is not a file: {norm_path_str} (use force=True to delete directories)",
                    "filepath": filepath
                }
            
            # Get file size for information
            if os.path.isfile(abs_filepath):
                file_size = os.path.getsize(abs_filepath)
                size_str = f"({file_size} bytes)"
                self.report_progress(f" {size_str}", end="")
            else:
                self.report_progress(" (directory)", end="")
            
            # Perform deletion
            if os.path.isfile(abs_filepath):
                os.remove(abs_filepath)
                message = f"Successfully deleted file {norm_path_str}"
            else:
                # This would be a directory if force=True
                os.rmdir(abs_filepath)
                message = f"Successfully deleted directory {norm_path_str}"
            
            self.report_result(message)
            
            return {
                "success": True,
                "filepath": filepath,
                "message": message,
                "force": force
            }
            
        except OSError as e:
            if e.errno == 39:  # Directory not empty
                self.report_error(f"Cannot delete non-empty directory: {norm_path_str} (use force=True with caution)")
                return {
                    "success": False,
                    "error": f"Cannot delete non-empty directory: {norm_path_str} (use force=True with caution)",
                    "filepath": filepath,
                    "force": force
                }
            else:
                self.report_error(f"OS Error deleting file: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "filepath": filepath,
                    "force": force
                }
        except Exception as e:
            self.report_error(f"Error deleting file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filepath": filepath,
                "force": force
            }


# CLI interface for testing
def main():
    """Command line interface for testing the DeleteFileTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete file tool for AI function calling")
    parser.add_argument("filepath", help="File path to delete")
    parser.add_argument("--force", "-f", action="store_true", help="Force deletion (allows deleting directories)")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = DeleteFile()
    result = tool_instance.run(
        filepath=args.filepath,
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
