#!/usr/bin/env python3
"""
Read File Lines Tool - A class-based tool for reading specific line ranges from a file.

This tool demonstrates how to use the base tool class with progress reporting.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.read_file_lines [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="r")
class ReadFileLines(BaseTool):
    """
    Tool for reading specific line ranges from a file (1-based indexing).
    """
    
    def run(self, filepath: str, from_line: Optional[int] = None, to_line: Optional[int] = None) -> Dict[str, Any]:
        """
        Read specific line ranges from a file (1-based indexing).
        
        Args:
            filepath (str): The path to the file to read
            from_line (int, optional): Starting line number (1-based). If None, starts from beginning.
            to_line (int, optional): Ending line number (1-based). If None, reads to end of file.
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'content': file content as string (if successful)
                - 'filepath': the file that was read
                - 'from_line': starting line number (1-based)
                - 'to_line': ending line number (1-based)
                - 'total_lines': total number of lines in the file
                - 'lines_read': number of lines actually read
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_filepath = os.path.abspath(filepath)
            norm_path_str = norm_path(abs_filepath)
            
            # Report start
            range_info = ""
            if from_line is not None and to_line is not None:
                range_info = f" (lines {from_line}-{to_line})"
            elif from_line is not None:
                range_info = f" (from line {from_line})"
            elif to_line is not None:
                range_info = f" (up to line {to_line})"
                
            self.report_start(f"Reading file {norm_path_str}{range_info}", end="")
            
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
            
            # Read the file and determine total lines
            with open(abs_filepath, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            
            # Validate line numbers
            if from_line is not None and (from_line < 1 or from_line > total_lines):
                error_msg = f"from_line ({from_line}) is out of range. File has {total_lines} lines."
                self.report_error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "filepath": filepath,
                    "total_lines": total_lines
                }
                
            if to_line is not None and (to_line < 1 or to_line > total_lines):
                error_msg = f"to_line ({to_line}) is out of range. File has {total_lines} lines."
                self.report_error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "filepath": filepath,
                    "total_lines": total_lines
                }
            
            # Set default values if not provided
            actual_from = from_line - 1 if from_line is not None else 0  # Convert to 0-based
            actual_to = to_line if to_line is not None else total_lines  # Keep as 1-based for slicing
            
            # Handle case where from_line > to_line
            if from_line is not None and to_line is not None and from_line > to_line:
                error_msg = f"from_line ({from_line}) cannot be greater than to_line ({to_line})"
                self.report_error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "filepath": filepath,
                    "total_lines": total_lines
                }
            
            # Extract the requested lines
            selected_lines = all_lines[actual_from:actual_to]
            content = ''.join(selected_lines)
            lines_read = len(selected_lines)
            
            # Determine actual line range read
            actual_from_line = actual_from + 1  # Convert back to 1-based
            actual_to_line = actual_from + lines_read  # 1-based end line
            
            self.report_result(f"Read {lines_read} lines (lines {actual_from_line}-{actual_to_line})")
            
            return {
                "success": True,
                "content": content,
                "filepath": filepath,
                "from_line": actual_from_line,
                "to_line": actual_to_line,
                "total_lines": total_lines,
                "lines_read": lines_read
            }
            
        except Exception as e:
            self.report_error(f"Error reading file: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filepath": filepath,
                "from_line": from_line,
                "to_line": to_line
            }


# CLI interface for testing
def main():
    """Command line interface for testing the ReadFileLines tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Read specific line ranges from a file (1-based indexing)")
    parser.add_argument("filepath", help="File path to read")
    parser.add_argument("--from-line", "-f", type=int, help="Starting line number (1-based)")
    parser.add_argument("--to-line", "-t", type=int, help="Ending line number (1-based)")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = ReadFileLines()
    result = tool_instance.run(
        filepath=args.filepath,
        from_line=args.from_line,
        to_line=args.to_line
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_path_str = norm_path(result['filepath'])
            from_line = result.get('from_line', 1)
            to_line = result.get('to_line', result['total_lines'])
            print(f"Content of '{norm_path_str}' (lines {from_line}-{to_line}):")
            print("-" * 40)
            print(result["content"])
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
