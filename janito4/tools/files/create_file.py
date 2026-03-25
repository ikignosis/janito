#!/usr/bin/env python3
"""
Create File Tool - A class-based tool for creating files with specified content.

This tool demonstrates how to use the base tool class with progress reporting.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito4.tools.files.create_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="w")
class CreateFile(BaseTool):
    """
    Tool for creating a new file with specified content.
    """
    
    def run(self, filepath: str, content: str = "", overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a new file with specified content.
        
        Args:
            filepath (str): The path where the file should be created
            content (str): Content to write to the file (default: empty string)
            overwrite (bool): Whether to overwrite existing file (default: False)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'filepath': the file that was created
                - 'bytes_written': number of bytes written
                - 'lines_written': number of lines written
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_filepath = os.path.abspath(filepath)
            norm_path_str = norm_path(abs_filepath)
            
            # Report start
            self.report_start(f"Creating file {norm_path_str}", end="")
            
            # Check if file exists and overwrite is not allowed
            if os.path.exists(abs_filepath) and not overwrite:
                self.report_error("File already exists; (use overwrite=True to replace)")
                return {
                    "success": False,
                    "error": f"File already exists: {norm_path_str} (use overwrite=True to replace)",
                    "filepath": filepath
                }
            
            # Create parent directories if they don't exist
            parent_dir = os.path.dirname(abs_filepath)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                self.report_progress(f" (created directories)", end="")
            
            # Write the content to the file
            with open(abs_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                bytes_written = len(content.encode('utf-8'))
                lines_written = content.count('\n') + (1 if content else 0) if content else 0
            
            self.report_result(f"Wrote {bytes_written} bytes ({lines_written} lines)")
            
            return {
                "success": True,
                "filepath": filepath,
                "bytes_written": bytes_written,
                "lines_written": lines_written,
                "overwrite": overwrite
            }
            
        except Exception as e:
            self.report_error(f"Error creating file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filepath": filepath,
                "overwrite": overwrite
            }


# CLI interface for testing
def main():
    """Command line interface for testing the CreateFileTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create file tool for AI function calling")
    parser.add_argument("filepath", help="File path to create")
    parser.add_argument("--content", "-c", default="", help="Content to write to the file")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite existing file")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = CreateFile()
    result = tool_instance.run(
        filepath=args.filepath,
        content=args.content,
        overwrite=args.overwrite
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_path_str = norm_path(result['filepath'])
            print(f"Successfully created file '{norm_path_str}'")
            print(f"Wrote {result['bytes_written']} bytes ({result['lines_written']} lines)")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()