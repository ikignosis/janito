#!/usr/bin/env python3
"""
Search Text Tool - A class-based tool for searching exact text in files.

This tool demonstrates how to use the base tool class with progress reporting.
It searches for exact text matches in files and returns matches with positions and content.
Optionally respects .gitignore patterns when enabled.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.search_text [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import os
from typing import Dict, Any, Optional, List
from ...tooling import BaseTool, norm_path
from ..decorator import tool


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
class SearchText(BaseTool):
    """
    Tool for searching exact text matches in files and directories.
    """
    
    def run(self, paths: str, query: str, case_sensitive: bool = True, 
            max_depth: Optional[int] = None, max_results: Optional[int] = 100, 
            count_only: bool = False, respect_gitignore: bool = True) -> Dict[str, Any]:
        """
        Search for exact text matches in files and directories.
        
        Args:
            paths (str): Space-separated paths to search in (directories or files)
            query (str): Exact text to search for
            case_sensitive (bool): If False, perform case-insensitive search
            max_depth (int, optional): Maximum directory depth to search (None = unlimited)
            max_results (int, optional): Maximum number of results to return (None = unlimited)
            count_only (bool): If True, return only match counts instead of matching lines
            respect_gitignore (bool): Whether to respect .gitignore patterns. Default is True.
        
        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'matches': list of matches formatted as 'filepath:lineno: line_content' (if count_only=False)
                - 'counts': dict with per-file and total match counts (if count_only=True)
                - 'total_matches': total number of matches found
                - 'files_searched': number of files searched
                - 'respect_gitignore': whether .gitignore was respected
                - 'gitignore_applied': whether .gitignore was actually applied
                - 'files_ignored_by_gitignore': number of files skipped due to .gitignore
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
                    "paths": paths,
                    "respect_gitignore": respect_gitignore
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
                    "paths": paths,
                    "respect_gitignore": respect_gitignore
                }
            
            # Load .gitignore for each directory path
            gitignore_specs = {}
            if respect_gitignore:
                for path in valid_paths:
                    if os.path.isdir(path):
                        spec = _load_gitignore_spec(path)
                        if spec:
                            gitignore_specs[path] = spec
            
            # Report start
            paths_str = ", ".join([norm_path(p) for p in valid_paths[:3]])
            if len(valid_paths) > 3:
                paths_str += f" (+{len(valid_paths) - 3} more)"
            gitignore_str = " (respecting .gitignore)" if gitignore_specs else ""
            self.report_start(f"Searching for exact text '{query}' in {paths_str}{gitignore_str}")
            
            # Perform search
            if count_only:
                result = self._search_count_only(
                    valid_paths, query, case_sensitive, max_depth, max_results, gitignore_specs
                )
            else:
                result = self._search_with_content(
                    valid_paths, query, case_sensitive, max_depth, max_results, gitignore_specs
                )
            
            if result["success"]:
                if count_only:
                    self.report_result(f"Found {result['total_matches']} matches in {result['files_searched']} files")
                else:
                    match_count = len(result['matches'])
                    self.report_result(f"Found {match_count} matches in {result['files_searched']} files")
            
            return result
            
        except Exception as e:
            self.report_error(f"Error during search: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "paths": paths,
                "query": query,
                "respect_gitignore": respect_gitignore
            }
    
    def _search_with_content(self, paths: List[str], query: str,
                           case_sensitive: bool, max_depth: Optional[int], 
                           max_results: Optional[int], 
                           gitignore_specs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search and return matching lines with content."""
        matches = []
        files_searched = 0
        files_ignored = 0
        
        for path in paths:
            gitignore_spec = gitignore_specs.get(path) if gitignore_specs else None
            if os.path.isfile(path):
                # Search single file
                file_matches = self._search_file(path, query, case_sensitive, max_results)
                if file_matches:
                    matches.extend(file_matches)
                    if max_results and len(matches) >= max_results:
                        matches = matches[:max_results]
                        break
                files_searched += 1
            else:
                # Search directory recursively
                dir_matches, dir_files_searched, dir_files_ignored = self._search_directory(
                    path, query, case_sensitive, max_depth, max_results, gitignore_spec
                )
                matches.extend(dir_matches)
                files_searched += dir_files_searched
                files_ignored += dir_files_ignored
                if max_results and len(matches) >= max_results:
                    matches = matches[:max_results]
                    break
        
        return {
            "success": True,
            "matches": matches,
            "total_matches": len(matches),
            "files_searched": files_searched,
            "respect_gitignore": bool(gitignore_specs),
            "gitignore_applied": any(gitignore_specs.values()) if gitignore_specs else False,
            "files_ignored_by_gitignore": files_ignored
        }
    
    def _search_count_only(self, paths: List[str], query: str,
                          case_sensitive: bool, max_depth: Optional[int], 
                          max_results: Optional[int],
                          gitignore_specs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search and return only match counts."""
        counts = {}
        total_matches = 0
        files_searched = 0
        files_ignored = 0
        
        for path in paths:
            gitignore_spec = gitignore_specs.get(path) if gitignore_specs else None
            if os.path.isfile(path):
                # Count matches in single file
                file_count = self._count_file_matches(path, query, case_sensitive)
                if file_count > 0:
                    counts[path] = file_count
                    total_matches += file_count
                files_searched += 1
            else:
                # Count matches in directory
                dir_counts, dir_total, dir_files, dir_ignored = self._count_directory_matches(
                    path, query, case_sensitive, max_depth, gitignore_spec
                )
                counts.update(dir_counts)
                total_matches += dir_total
                files_searched += dir_files
                files_ignored += dir_ignored
        
        return {
            "success": True,
            "counts": counts,
            "total_matches": total_matches,
            "files_searched": files_searched,
            "respect_gitignore": bool(gitignore_specs),
            "gitignore_applied": any(gitignore_specs.values()) if gitignore_specs else False,
            "files_ignored_by_gitignore": files_ignored
        }
    
    def _search_file(self, filepath: str, query: str, 
                    case_sensitive: bool, max_results: Optional[int]) -> List[str]:
        """Search a single file and return matching lines."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                matches = []
                for lineno, line in enumerate(f, 1):
                    line_content = line.rstrip('\n')
                    if case_sensitive:
                        if query in line_content:
                            matches.append(f"{filepath}:{lineno}: {line_content}")
                    else:
                        if query.lower() in line_content.lower():
                            matches.append(f"{filepath}:{lineno}: {line_content}")
                    
                    if max_results and len(matches) >= max_results:
                        break
                
                return matches
        except Exception:
            # Skip files that can't be read (binary files, permission issues, etc.)
            return []
    
    def _count_file_matches(self, filepath: str, query: str, case_sensitive: bool) -> int:
        """Count matches in a single file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                count = 0
                for line in f:
                    line_content = line.rstrip('\n')
                    if case_sensitive:
                        if query in line_content:
                            count += 1
                    else:
                        if query.lower() in line_content.lower():
                            count += 1
                return count
        except Exception:
            # Skip files that can't be read
            return 0
    
    def _search_directory(self, dirpath: str, query: str, case_sensitive: bool,
                         max_depth: Optional[int], max_results: Optional[int],
                         gitignore_spec = None) -> tuple:
        """Search a directory recursively and return matches."""
        matches = []
        files_searched = 0
        files_ignored = 0
        
        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if max_depth is not None:
                    current_depth = root[len(dirpath):].count(os.sep)
                    if current_depth >= max_depth:
                        dirs.clear()  # Don't recurse deeper
                        continue
                
                # Filter out ignored directories (modify in-place to prevent walking into them)
                if gitignore_spec:
                    rel_root = os.path.relpath(root, dirpath)
                    dirs[:] = [
                        d for d in dirs
                        if not _is_ignored_by_gitignore(
                            os.path.join(rel_root, d) if rel_root != "." else d,
                            gitignore_spec
                        )
                    ]
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, dirpath)
                    
                    # Skip if ignored by .gitignore
                    if gitignore_spec and _is_ignored_by_gitignore(rel_path, gitignore_spec):
                        files_ignored += 1
                        continue
                    
                    file_matches = self._search_file(filepath, query, case_sensitive, 
                                                   max_results - len(matches) if max_results else None)
                    if file_matches:
                        matches.extend(file_matches)
                        if max_results and len(matches) >= max_results:
                            files_searched += 1
                            return matches[:max_results], files_searched, files_ignored
                    
                    files_searched += 1
        
        except Exception:
            pass  # Skip directories that can't be accessed
        
        return matches, files_searched, files_ignored
    
    def _count_directory_matches(self, dirpath: str, query: str, 
                               case_sensitive: bool, max_depth: Optional[int],
                               gitignore_spec = None) -> tuple:
        """Count matches in a directory recursively."""
        counts = {}
        total_matches = 0
        files_searched = 0
        files_ignored = 0
        
        try:
            for root, dirs, files in os.walk(dirpath):
                # Check depth limit
                if max_depth is not None:
                    current_depth = root[len(dirpath):].count(os.sep)
                    if current_depth >= max_depth:
                        dirs.clear()  # Don't recurse deeper
                        continue
                
                # Filter out ignored directories (modify in-place to prevent walking into them)
                if gitignore_spec:
                    rel_root = os.path.relpath(root, dirpath)
                    dirs[:] = [
                        d for d in dirs
                        if not _is_ignored_by_gitignore(
                            os.path.join(rel_root, d) if rel_root != "." else d,
                            gitignore_spec
                        )
                    ]
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, dirpath)
                    
                    # Skip if ignored by .gitignore
                    if gitignore_spec and _is_ignored_by_gitignore(rel_path, gitignore_spec):
                        files_ignored += 1
                        continue
                    
                    file_count = self._count_file_matches(filepath, query, case_sensitive)
                    if file_count > 0:
                        counts[filepath] = file_count
                        total_matches += file_count
                    files_searched += 1
        
        except Exception:
            pass  # Skip directories that can't be accessed
        
        return counts, total_matches, files_searched, files_ignored


# CLI interface for testing
def main():
    """Command line interface for testing the SearchText tool."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Search exact text tool for AI function calling")
    parser.add_argument("paths", help="Space-separated paths to search in")
    parser.add_argument("query", help="Exact text to search for")
    parser.add_argument("--ignore-case", "-i", action="store_true", help="Case insensitive search")
    parser.add_argument("--max-depth", "-d", type=int, help="Maximum directory depth")
    parser.add_argument("--max-results", "-m", type=int, default=100, help="Maximum results")
    parser.add_argument("--count-only", "-c", action="store_true", help="Return only counts")
    parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore filtering")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    tool_instance = SearchText()
    result = tool_instance.run(
        paths=args.paths,
        query=args.query,
        case_sensitive=not args.ignore_case,
        max_depth=args.max_depth,
        max_results=args.max_results,
        count_only=args.count_only,
        respect_gitignore=not args.no_gitignore
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if args.count_only:
                print(f"Total matches: {result['total_matches']}")
                print(f"Files searched: {result['files_searched']}")
                if result.get('gitignore_applied'):
                    print(f"Respecting .gitignore")
                ignored = result.get('files_ignored_by_gitignore', 0)
                if ignored > 0:
                    print(f"Files ignored by .gitignore: {ignored}")
                if result['counts']:
                    print("\nPer-file counts:")
                    for filepath, count in result['counts'].items():
                        print(f"  {norm_path(filepath)}: {count}")
            else:
                print(f"Found {len(result['matches'])} matches in {result['files_searched']} files:")
                if result.get('gitignore_applied'):
                    print(f"Respecting .gitignore")
                ignored = result.get('files_ignored_by_gitignore', 0)
                if ignored > 0:
                    print(f"Files ignored by .gitignore: {ignored}")
                for match in result['matches']:
                    print(f"  {match}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
