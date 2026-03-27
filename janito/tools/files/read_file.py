#!/usr/bin/env python3
"""
Read File Tool - A class-based tool for reading file contents.

This tool demonstrates how to use the base tool class with progress reporting.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.read_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="r")
class ReadFile(BaseTool):
    """
    Tool for reading the contents of a file.
    """
    
    def run(self, filepath: str, max_lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Read the contents of a file.
        
        Args:
            filepath (str): The path to the file to read
            max_lines (int, optional): Maximum number of lines to read (for large files)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'content': file content as string (if successful)
                - 'filepath': the file that was read
                - 'lines_read': number of lines read
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_filepath = os.path.abspath(filepath)
            norm_path_str = norm_path(abs_filepath)
            
            # Report start
            self.report_start(f"📖 Reading file {norm_path_str}", end="")
            
            if not os.path.exists(abs_filepath):
                self.report_error(f"File does not exist: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"File does not exist: {norm_path_str}",
                    "filepath": filepath
                }
            
            if not os.path.isfile(abs_filepath):
                self.report_error(f"Path is not a file: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"Path is not a file: {norm_path_str}",
                    "filepath": filepath
                }
            
            # Get file size for progress indication
            file_size = os.path.getsize(abs_filepath)
            size_str = f"({file_size} bytes)"
            self.report_progress(f" {size_str}", end="")
            
            with open(abs_filepath, 'r', encoding='utf-8') as f:
                if max_lines is not None:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)
                    lines_read = len(lines)
                else:
                    content = f.read()
                    lines_read = content.count('\n') + 1
            
            self.report_result(f"Read {lines_read} lines")
            
            return {
                "success": True,
                "content": content,
                "filepath": filepath,
                "lines_read": lines_read,
                "max_lines": max_lines
            }
            
        except Exception as e:
            self.report_error(f"Error reading file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filepath": filepath,
                "max_lines": max_lines
            }


# CLI interface for testing
def main():
    """Command line interface for testing the ReadFileTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Read file tool for AI function calling")
    parser.add_argument("filepath", help="File path to read")
    parser.add_argument("--max-lines", "-m", type=int, help="Maximum number of lines to read")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = ReadFile()
    result = tool_instance.run(
        filepath=args.filepath,
        max_lines=args.max_lines
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_path_str = norm_path(result['filepath'])
            print(f"Content of '{norm_path_str}':")
            print("-" * 40)
            print(result["content"])
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
