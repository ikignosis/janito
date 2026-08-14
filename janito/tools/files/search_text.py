#!/usr/bin/env python3
"""
Search Text Tool - A class-based tool for searching exact text in files.

This tool demonstrates how to use the base tool class with progress reporting.
It searches for exact text matches in files and returns matches with positions and content.
Optionally respects .gitignore patterns when enabled, and always respects
.janitoignore patterns.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.search_text [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
from typing import Any

from ...tooling import norm_path
from ...tooling.decorator import tool
from .search_base import SearchRunner, print_search_result


@tool(permissions="r")
class SearchText(SearchRunner):
    """
    Tool for searching exact text matches in files and directories.

    Args:
        paths (str): Space-separated paths to search in (directories or files)
        query (str): Exact text to search for
        case_sensitive (bool): If False, perform case-insensitive search
        max_depth (int, optional): Maximum directory depth to search (None = unlimited)
        max_results (int, optional): Maximum number of results to return (None = unlimited)
        count_only (bool): If True, return only match counts instead of matching lines
        respect_gitignore (bool): Whether to respect .gitignore patterns.
            .janitoignore patterns are always respected. Default is True.
        exclude (str, optional): Space-separated glob patterns to exclude
            (e.g. "*/node_modules/* */__pycache__/*").
    """

    term_key = "query"
    error_label = "search"

    def start_message(
        self, term: str, paths_str: str, exclude_str: str | None = None
    ) -> str:
        """Return the report_start message for this tool."""
        message = f"\U0001f50d Searching for exact text '{term}' in {paths_str}"
        if exclude_str:
            message += f" exclude '{exclude_str}'"
        return message

    def run(
        self,
        paths: str,
        query: str,
        case_sensitive: bool = True,
        max_depth: int | None = None,
        max_results: int | None = 100,
        count_only: bool = False,
        respect_gitignore: bool = True,
        exclude: str | None = None,
    ) -> dict[str, Any]:
        """
        Search for exact text matches in files and directories.

        Args:
            paths (str): Space-separated paths to search in (directories or files)
            query (str): Exact text to search for
            case_sensitive (bool): If False, perform case-insensitive search
            max_depth (int, optional): Maximum directory depth to search (None = unlimited)
            max_results (int, optional): Maximum number of results to return (None = unlimited)
            count_only (bool): If True, return only match counts instead of matching lines
            respect_gitignore (bool): Whether to respect .gitignore patterns.
                .janitoignore patterns are always respected. Default is True.
            exclude (str, optional): Space-separated glob patterns to exclude
                (e.g. "*/node_modules/* */__pycache__/*").

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
        return self.run_search(
            paths,
            query,
            case_sensitive=case_sensitive,
            max_depth=max_depth,
            max_results=max_results,
            count_only=count_only,
            respect_gitignore=respect_gitignore,
            exclude=exclude,
        )

    def _line_matches(
        self, query: str, line_content: str, case_sensitive: bool
    ) -> bool:
        """Return whether ``line_content`` contains ``query``."""
        if case_sensitive:
            return query in line_content
        return query.lower() in line_content.lower()

    def _search_file(
        self,
        filepath: str,
        query: str,
        case_sensitive: bool,
        max_results: int | None,
    ) -> list[str]:
        """Search a single file and return matching lines."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                matches = []
                display_path = norm_path(filepath)
                for lineno, line in enumerate(f, 1):
                    line_content = line.rstrip("\n")
                    if self._line_matches(query, line_content, case_sensitive):
                        matches.append(f"{display_path}:{lineno}: {line_content}")

                    if max_results and len(matches) >= max_results:
                        break

                return matches
        except Exception:
            # Skip files that can't be read (binary files, permission issues, etc.)
            return []

    def _count_file_matches(
        self, filepath: str, query: str, case_sensitive: bool
    ) -> int:
        """Count matches in a single file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                count = 0
                for line in f:
                    line_content = line.rstrip("\n")
                    if self._line_matches(query, line_content, case_sensitive):
                        count += 1
                return count
        except Exception:
            # Skip files that can't be read
            return 0


# CLI interface for testing
def main():
    """Command line interface for testing the SearchText tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Search text tool for AI function calling"
    )
    parser.add_argument("paths", help="Space-separated paths to search in")
    parser.add_argument("query", help="Exact text to search for")
    parser.add_argument(
        "--ignore-case", "-i", action="store_true", help="Case insensitive search"
    )
    parser.add_argument("--max-depth", "-d", type=int, help="Maximum directory depth")
    parser.add_argument(
        "--max-results", "-m", type=int, default=100, help="Maximum results"
    )
    parser.add_argument(
        "--count-only", "-c", action="store_true", help="Return only counts"
    )
    parser.add_argument(
        "--no-gitignore", action="store_true", help="Disable .gitignore filtering"
    )
    parser.add_argument(
        "--exclude",
        "-e",
        help="Space-separated glob patterns to exclude",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    tool_instance = SearchText()
    result = tool_instance.run(
        paths=args.paths,
        query=args.query,
        case_sensitive=not args.ignore_case,
        max_depth=args.max_depth,
        max_results=args.max_results,
        count_only=args.count_only,
        respect_gitignore=not args.no_gitignore,
        exclude=args.exclude,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_search_result(result, args.count_only)


if __name__ == "__main__":
    main()
