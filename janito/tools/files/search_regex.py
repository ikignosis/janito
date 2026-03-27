#!/usr/bin/env python3
"""
Search Regex Tool - A class-based tool for searching regular expression patterns in files.

This tool demonstrates how to use the base tool class with progress reporting.
It searches for regex patterns in files and returns matches with positions and content.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.search_regex [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
import re
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool, norm_path
from ..decorator import tool


@tool(permissions="r")
class SearchRegex(BaseTool):
    """
    Tool for searching regular expression patterns in files and directories.
    """
    
    def run(self, paths: str, pattern: str, case_sensitive: bool = True, 
            max_depth: Optional[int] = None, max_results: Optional[int] = 100, 
            count_only: bool = False) -> Dict[str, Any]:
        """
        Search for regular expression patterns in files and directories.
        
        Args:
            paths (str): Space-separated paths to search in (directories or files)
            pattern (str): Regular expression pattern to search for
            case_sensitive (bool): If False, perform case-insensitive search
            max_depth (int, optional): Maximum directory depth to search (None = unlimited)
            max_results (int, optional): Maximum number of results to return (None = unlimited)
            count_only (bool): If True, return only match counts instead of matching lines
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'matches': list of matches formatted as 'filepath:lineno: line_content' (if count_only=False)
                - 'counts': dict with per-file and total match counts (if count_only=True)
                - 'total_matches': total number of matches found
                - 'files_searched': number of files searched
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            # Parse paths
            path_list = paths.strip().split()
            if not path_list:
                self.report_error("No paths provided")
                return {
                    "success": False,
                    "error": "No paths provided",
                    "paths": paths
                }
            
            # Validate paths exist
            valid_paths = []
            for path in path_list:
                abs_path = os.path.abspath(path)
                if not os.path.exists(abs_path):
                    self.report_warning(f"Path does not exist: {norm_path(abs_path)}")
                    continue
                valid_paths.append(abs_path)
            
            if not valid_paths:
                self.report_error("No valid paths to search")
                return {
                    "success": False,
                    "error": "No valid paths to search",
                    "paths": paths
                }
            
            # Report start
            paths_str = ", ".join([norm_path(p) for p in valid_paths[:3]])
            if len(valid_paths) > 3:
                paths_str += f" (+{len(valid_paths) - 3} more)"
            self.report_start(f"Searching regex pattern '{pattern}' in {paths_str}")
            
            # Perform search
            if count_only:
                result = self._search_count_only(
                    valid_paths, pattern, case_sensitive, max_depth, max_results
                )
            else:
                result = self._search_with_content(
                    valid_paths, pattern, case_sensitive, max_depth, max_results
                )
            
            if result["success"]:
                if count_only:
                    self.report_result(f"Found {result['total_matches']} matches in {result['files_searched']} files")
                else:
                    match_count = len(result['matches'])
                    self.report_result(f"Found {match_count} matches in {result['files_searched']} files")
            
            return result
            
        except Exception as e:
            self.report_error(f"Error during regex search: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "paths": paths,
                "pattern": pattern
            }
    
    def _search_with_content(self, paths: List[str], pattern: str,
                           case_sensitive: bool, max_depth: Optional[int], 
                           max_results: Optional[int]) -> Dict[str, Any]:
        """Search and return matching lines with content."""
        matches = []
        files_searched = 0
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for path in paths:
            if os.path.isfile(path):
                # Search single file
                file_matches = self._search_file(path, pattern, flags, max_results)
                if file_matches:
                    matches.extend(file_matches)
                    if max_results and len(matches) >= max_results:
                        matches = matches[:max_results]
                        break
                files_searched += 1
            else:
                # Search directory recursively
                dir_matches, dir_files_searched = self._search_directory(
                    path, pattern, flags, max_depth, max_results
                )
                matches.extend(dir_matches)
                files_searched += dir_files_searched
                if max_results and len(matches) >= max_results:
                    matches = matches[:max_results]
                    break
        
        return {
            "success": True,
            "matches": matches,
            "total_matches": len(matches),
            "files_searched": files_searched
        }
    
    def _search_count_only(self, paths: List[str], pattern: str,
                          case_sensitive: bool, max_depth: Optional[int], 
                          max_results: Optional[int]) -> Dict[str, Any]:
        """Search and return only match counts."""
        counts = {}
        total_matches = 0
        files_searched = 0
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for path in paths:
            if os.path.isfile(path):
                # Count matches in single file
                file_count = self._count_file_matches(path, pattern, flags)
                if file_count > 0:
                    counts[path] = file_count
                    total_matches += file_count
                files_searched += 1
            else:
                # Count matches in directory
                dir_counts, dir_total, dir_files = self._count_directory_matches(
                    path, pattern, flags, max_depth
                )
                counts.update(dir_counts)
                total_matches += dir_total
                files_searched += dir_files
        
        return {
            "success": True,
            "counts": counts,
            "total_matches": total_matches,
            "files_searched": files_searched
        }
    
    def _search_file(self, filepath: str, pattern: str, flags: int, 
                    max_results: Optional[int]) -> List[str]:
        """Search a single file and return matching lines."""
        try:
            compiled_pattern = re.compile(pattern, flags)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                matches = []
                for lineno, line in enumerate(f, 1):
                    line_content = line.rstrip('\n')
                    if compiled_pattern.search(line_content):
                        matches.append(f"{filepath}:{lineno}: {line_content}")
                    
                    if max_results and len(matches) >= max_results:
                        break
                
                return matches
        except re.error as e:
            self.report_error(f"Invalid regex pattern '{pattern}': {str(e)}")
            return []
        except Exception:
            # Skip files that can't be read (binary files, permission issues, etc.)
            return []
    
    def _count_file_matches(self, filepath: str, pattern: str, flags: int) -> int:
        """Count matches in a single file."""
        try:
            compiled_pattern = re.compile(pattern, flags)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                count = 0
                for line in f:
                    line_content = line.rstrip('\n')
                    if compiled_pattern.search(line_content):
                        count += 1
                return count
        except re.error:
            # Invalid regex pattern
            return 0
        except Exception:
            # Skip files that can't be read
            return 0
    
    def _search_directory(self, dirpath: str, pattern: str, flags: int,
                         max_depth: Optional[int], max_results: Optional[int]) -> tuple:
        """Search a directory recursively and return matches."""
        matches = []
        files_searched = 0
        
        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if max_depth is not None:
                    current_depth = root[len(dirpath):].count(os.sep)
                    if current_depth >= max_depth:
                        dirs.clear()  # Don't recurse deeper
                        continue
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    file_matches = self._search_file(filepath, pattern, flags, 
                                                   max_results - len(matches) if max_results else None)
                    if file_matches:
                        matches.extend(file_matches)
                        if max_results and len(matches) >= max_results:
                            files_searched += 1
                            return matches[:max_results], files_searched
                    
                    files_searched += 1
        
        except Exception:
            pass  # Skip directories that can't be accessed
        
        return matches, files_searched
    
    def _count_directory_matches(self, dirpath: str, pattern: str, 
                               flags: int, max_depth: Optional[int]) -> tuple:
        """Count matches in a directory recursively."""
        counts = {}
        total_matches = 0
        files_searched = 0
        
        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if max_depth is not None:
                    current_depth = root[len(dirpath):].count(os.sep)
                    if current_depth >= max_depth:
                        dirs.clear()  # Don't recurse deeper
                        continue
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    file_count = self._count_file_matches(filepath, pattern, flags)
                    if file_count > 0:
                        counts[filepath] = file_count
                        total_matches += file_count
                    files_searched += 1
        
        except Exception:
            pass  # Skip directories that can't be accessed
        
        return counts, total_matches, files_searched


# CLI interface for testing
def main():
    """Command line interface for testing the SearchRegex tool."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Search regex tool for AI function calling")
    parser.add_argument("paths", help="Space-separated paths to search in")
    parser.add_argument("pattern", help="Regular expression pattern to search for")
    parser.add_argument("--ignore-case", "-i", action="store_true", help="Case insensitive search")
    parser.add_argument("--max-depth", "-d", type=int, help="Maximum directory depth")
    parser.add_argument("--max-results", "-m", type=int, default=100, help="Maximum results")
    parser.add_argument("--count-only", "-c", action="store_true", help="Return only counts")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = SearchRegex()
    result = tool_instance.run(
        paths=args.paths,
        pattern=args.pattern,
        case_sensitive=not args.ignore_case,
        max_depth=args.max_depth,
        max_results=args.max_results,
        count_only=args.count_only
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if args.count_only:
                print(f"Total matches: {result['total_matches']}")
                print(f"Files searched: {result['files_searched']}")
                if result['counts']:
                    print("\nPer-file counts:")
                    for filepath, count in result['counts'].items():
                        print(f"  {norm_path(filepath)}: {count}")
            else:
                print(f"Found {len(result['matches'])} matches in {result['files_searched']} files:")
                for match in result['matches']:
                    print(f"  {match}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
