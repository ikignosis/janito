#!/usr/bin/env python3
"""
Read Multiple Files Tool - A class-based tool for reading multiple file contents.

This tool demonstrates how to use the base tool class with progress reporting.
It extends the functionality of ReadFile to handle multiple files in a single operation.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.read_multiple_files [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import json
from typing import Dict, Any, List, Optional
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="r")
class ReadMultipleFiles(BaseTool):
    """
    Tool for reading the contents of multiple files.
    """
    
    def run(self, filepaths: List[str], max_lines: Optional[int] = None) -> Dict[str, Any]:
        """
        Read the contents of multiple files.
        
        Args:
            filepaths (List[str]): List of file paths to read
            max_lines (int, optional): Maximum number of lines to read per file (for large files)
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded (at least one file read)
                - 'files': list of dictionaries with individual file results
                - 'total_files': number of files processed
                - 'successful_files': number of files successfully read
                - 'error': error message if operation failed completely (only present if success=False)
        """
        if not filepaths or len(filepaths) == 0:
            self.report_error("No file paths provided")
            return {
                "success": False,
                "error": "No file paths provided",
                "total_files": 0,
                "successful_files": 0,
                "files": []
            }
        
        # Normalize the list (strip whitespace from each path)
        filepath_list = [path.strip() for path in filepaths if path and path.strip()]
        
        if not filepath_list:
            self.report_error("No valid file paths provided")
            return {
                "success": False,
                "error": "No valid file paths provided",
                "total_files": 0,
                "successful_files": 0,
                "files": []
            }
        
        try:
            # Report start
            self.report_start(f"📖 Reading {len(filepath_list)} files", end="")
            
            results = []
            successful_count = 0
            
            for i, filepath in enumerate(filepath_list):
                try:
                    abs_filepath = os.path.abspath(filepath)
                    norm_path_str = norm_path(abs_filepath)
                    
                    # Show progress for each file
                    if len(filepath_list) > 1:
                        self.report_progress(f"\n  [{i+1}/{len(filepath_list)}] {norm_path_str}", end="")
                    else:
                        self.report_progress(f" {norm_path_str}", end="")
                    
                    if not os.path.exists(abs_filepath):
                        error_result = {
                            "filepath": filepath,
                            "success": False,
                            "error": f"File does not exist: {norm_path_str}"
                        }
                        results.append(error_result)
                        continue
                    
                    if not os.path.isfile(abs_filepath):
                        error_result = {
                            "filepath": filepath,
                            "success": False,
                            "error": f"Path is not a file: {norm_path_str}"
                        }
                        results.append(error_result)
                        continue
                    
                    # Get file size for progress indication
                    file_size = os.path.getsize(abs_filepath)
                    if file_size > 0:
                        size_str = f"({file_size} bytes)"
                        self.report_progress(f" {size_str}", end="")
                    
                    with open(abs_filepath, 'r', encoding='utf-8') as f:
                        if max_lines is not None:
                            lines = []
                            for j, line in enumerate(f):
                                if j >= max_lines:
                                    break
                                lines.append(line.rstrip('\n'))
                            content = '\n'.join(lines)
                            lines_read = len(lines)
                        else:
                            content = f.read()
                            lines_read = content.count('\n') + 1
                    
                    success_result = {
                        "filepath": filepath,
                        "success": True,
                        "content": content,
                        "lines_read": lines_read,
                        "max_lines": max_lines
                    }
                    results.append(success_result)
                    successful_count += 1
                    
                except Exception as e:
                    error_result = {
                        "filepath": filepath,
                        "success": False,
                        "error": str(e)
                    }
                    results.append(error_result)
            
            # Report final results
            total_files = len(filepath_list)
            if successful_count == total_files:
                self.report_result(f"Successfully read all {successful_count} files")
            elif successful_count > 0:
                self.report_result(f"Read {successful_count}/{total_files} files successfully")
            else:
                self.report_error(f"Failed to read any of the {total_files} files")
            
            return {
                "success": successful_count > 0,
                "files": results,
                "total_files": total_files,
                "successful_files": successful_count,
                "max_lines": max_lines
            }
            
        except Exception as e:
            self.report_error(f"Error during multiple file reading: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_files": len(filepath_list) if 'filepath_list' in locals() else 0,
                "successful_files": 0,
                "files": []
            }


# CLI interface for testing
def main():
    """Command line interface for testing the ReadMultipleFilesTool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Read multiple files tool for AI function calling")
    parser.add_argument("filepaths", nargs="+", help="File paths to read (multiple arguments)")
    parser.add_argument("--max-lines", "-m", type=int, help="Maximum number of lines to read per file")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = ReadMultipleFiles()
    result = tool_instance.run(
        filepaths=args.filepaths,
        max_lines=args.max_lines
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Successfully read {result['successful_files']} out of {result['total_files']} files:")
            print("-" * 50)
            for file_result in result["files"]:
                if file_result["success"]:
                    norm_path_str = norm_path(file_result['filepath'])
                    print(f"\nContent of '{norm_path_str}':")
                    print("=" * 40)
                    print(file_result["content"])
                else:
                    print(f"\n? Error reading '{file_result['filepath']}': {file_result['error']}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
