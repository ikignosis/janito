#!/usr/bin/env python3
"""
List Files Tool - A class-based tool for listing files and directories.

This tool can be injected into AI clients to allow them to explore file systems.
It provides the ability to list files in a directory, with optional filtering by pattern.
Optionally respects .gitignore patterns when enabled, and always respects
.janitoignore patterns.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.list_files [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool
from .gitignore_utils import (
    is_ignored_by_gitignore,
    load_gitignore_spec,
    load_janitoignore_spec,
)


def _matches_pattern(filename: str, pattern: str) -> bool:
    """
    Check if filename matches the given pattern using Unix shell-style wildcards.

    Args:
        filename (str): The filename to check
        pattern (str): The pattern to match against (e.g., "*.py", "data_??.csv")

    Returns:
        bool: True if filename matches pattern, False otherwise
    """
    import fnmatch

    return fnmatch.fnmatch(filename, pattern)


@tool(permissions="r")
class ListFiles(BaseTool):
    """
    Tool for listing files and directories in the specified path.
    """

    def run(
        self,
        directory: str = ".",
        pattern: str | None = None,
        recursive: bool = False,
        max_depth: int | None = None,
        respect_gitignore: bool = True,
    ) -> dict[str, Any]:
        """
        List files and directories in the specified path.

        Args:
            directory (str): The directory path to list. Default is current directory (".").
            pattern (str, optional): File pattern to filter results (e.g., "*.py", "data_*.csv").
            recursive (bool): Whether to list files recursively. Default is False.
            max_depth (int, optional): Maximum depth for recursive listing. Default is None (unlimited).
            respect_gitignore (bool): Whether to respect .gitignore patterns.
                .janitoignore patterns are always respected. Default is True.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'files': list of file/directory paths
                - 'directory': the directory that was listed
                - 'pattern': the pattern used for filtering (if any)
                - 'recursive': whether recursive listing was used
                - 'respect_gitignore': whether .gitignore was respected
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            # Resolve the directory path
            abs_directory = os.path.abspath(directory)

            norm_dir = norm_path(abs_directory)

            if not os.path.exists(abs_directory):
                self.report_error(f"Directory does not exist: {norm_dir}")
                return {
                    "success": False,
                    "error": f"Directory does not exist: {norm_dir}",
                    "directory": directory,
                    "pattern": pattern,
                    "recursive": recursive,
                    "respect_gitignore": respect_gitignore,
                }

            if not os.path.isdir(abs_directory):
                self.report_error(f"Path is not a directory: {norm_dir}")
                return {
                    "success": False,
                    "error": f"Path is not a directory: {norm_dir}",
                    "directory": directory,
                    "pattern": pattern,
                    "recursive": recursive,
                    "respect_gitignore": respect_gitignore,
                }

            # Load ignore specs from the current working directory.
            # .janitoignore is always respected; .gitignore only when enabled.
            cwd = os.getcwd()
            gitignore_spec = None
            if respect_gitignore:
                gitignore_spec = load_gitignore_spec(cwd)
            janitoignore_spec = load_janitoignore_spec(cwd)

            # Report start of operation
            recursive_str = "recursively" if recursive else ""
            self.report_start(f"📁 Listing files at {norm_dir} {recursive_str}", end="")

            files = []
            dir_count = 0
            file_count = 0
            gitignore_ignored = 0
            janitoignore_ignored = 0

            def _is_ignored(rel_to_cwd: str, is_dir: bool = False) -> bool:
                """Check a path (relative to cwd) against .janitoignore then .gitignore."""
                nonlocal gitignore_ignored, janitoignore_ignored
                if janitoignore_spec and is_ignored_by_gitignore(
                    rel_to_cwd, janitoignore_spec, is_dir=is_dir
                ):
                    janitoignore_ignored += 1
                    return True
                if gitignore_spec and is_ignored_by_gitignore(
                    rel_to_cwd, gitignore_spec, is_dir=is_dir
                ):
                    gitignore_ignored += 1
                    return True
                return False

            if recursive:
                if max_depth is None:
                    for root, dirs, filenames in os.walk(abs_directory):
                        # Filter out ignored directories (modify in-place to prevent walking into them)
                        dirs[:] = [
                            d
                            for d in dirs
                            if not _is_ignored(
                                os.path.relpath(os.path.join(root, d), cwd),
                                is_dir=True,
                            )
                        ]

                        dir_count += len(dirs)
                        file_count += len(filenames)

                        for name in dirs + filenames:
                            full_path = os.path.join(root, name)
                            rel_path = os.path.relpath(full_path, abs_directory)
                            name_is_dir = name in dirs

                            # Skip if ignored by .janitoignore / .gitignore
                            if _is_ignored(
                                os.path.relpath(full_path, cwd),
                                is_dir=name_is_dir,
                            ):
                                continue

                            if pattern is None or _matches_pattern(name, pattern):
                                files.append(rel_path if rel_path != "." else name)
                else:
                    # Walk with depth limit
                    for root, dirs, filenames in os.walk(abs_directory):
                        depth = root[len(abs_directory) :].count(os.sep)
                        if depth <= max_depth:
                            # Filter out ignored directories
                            dirs[:] = [
                                d
                                for d in dirs
                                if not _is_ignored(
                                    os.path.relpath(os.path.join(root, d), cwd),
                                    is_dir=True,
                                )
                            ]

                            dir_count += len(dirs)
                            file_count += len(filenames)

                            for name in dirs + filenames:
                                full_path = os.path.join(root, name)
                                rel_path = os.path.relpath(full_path, abs_directory)
                                name_is_dir = name in dirs

                                # Skip if ignored by .janitoignore / .gitignore
                                if _is_ignored(
                                    os.path.relpath(full_path, cwd),
                                    is_dir=name_is_dir,
                                ):
                                    continue

                                if pattern is None or _matches_pattern(name, pattern):
                                    files.append(rel_path if rel_path != "." else name)
                        else:
                            dirs[:] = []  # Don't recurse further
            else:
                # Non-recursive listing
                items = os.listdir(abs_directory)
                for item in items:
                    item_path = os.path.join(abs_directory, item)
                    is_dir = os.path.isdir(item_path)

                    # Skip if ignored by .janitoignore / .gitignore (match relative to cwd)
                    if _is_ignored(os.path.relpath(item_path, cwd), is_dir=is_dir):
                        continue

                    if is_dir:
                        dir_count += 1
                    else:
                        file_count += 1
                    if pattern is None or _matches_pattern(item, pattern):
                        files.append(item)

            # Sort files for consistent output
            files.sort()

            # Report results
            total_found = len(files)
            ignore_msgs = []
            if gitignore_ignored:
                ignore_msgs.append(f"{gitignore_ignored} ignored by .gitignore")
            if janitoignore_ignored:
                ignore_msgs.append(f"{janitoignore_ignored} ignored by .janitoignore")
            ignore_msg = f", {', '.join(ignore_msgs)}" if ignore_msgs else ""
            self.report_result(
                f"Found {total_found} items ({file_count} files, {dir_count} dirs){ignore_msg}"
            )

            return {
                "success": True,
                "files": files,
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "max_depth": max_depth,
                "respect_gitignore": respect_gitignore,
                "gitignore_applied": gitignore_spec is not None,
                "janitoignore_applied": janitoignore_spec is not None,
                "stats": {
                    "total_items": total_found,
                    "files": file_count,
                    "directories": dir_count,
                    "gitignore_ignored": gitignore_ignored,
                    "janitoignore_ignored": janitoignore_ignored,
                },
            }

        except Exception as e:
            self.report_error(f"Error during file listing: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "max_depth": max_depth,
                "respect_gitignore": respect_gitignore,
            }


# CLI interface for testing
def main():
    """Command line interface for testing the ListFilesTool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="List files tool for AI function calling"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to list (default: current directory)",
    )
    parser.add_argument(
        "--pattern", "-p", help="File pattern to filter results (e.g., '*.py')"
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="List files recursively"
    )
    parser.add_argument(
        "--max-depth", "-d", type=int, help="Maximum depth for recursive listing"
    )
    parser.add_argument(
        "--no-gitignore", action="store_true", help="Disable .gitignore filtering"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    tool_instance = ListFiles()
    result = tool_instance.run(
        directory=args.directory,
        pattern=args.pattern,
        recursive=args.recursive,
        max_depth=args.max_depth,
        respect_gitignore=not args.no_gitignore,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_dir = norm_path(result["directory"])
            print(f"Files in '{norm_dir}':")
            if result["pattern"]:
                print(f"Pattern: {result['pattern']}")
            if result["recursive"]:
                print("Recursive listing enabled")
                if result.get("max_depth"):
                    print(f"Max depth: {result['max_depth']}")
            if result.get("gitignore_applied"):
                print("Respecting .gitignore")
            if result.get("janitoignore_applied"):
                print("Respecting .janitoignore")
            print("-" * 40)
            for file in result["files"]:
                print(file)
            stats = result.get("stats", {})
            ignore_filters = []
            if stats.get("gitignore_ignored", 0) > 0:
                ignore_filters.append(
                    f".gitignore filtered {stats['gitignore_ignored']} items"
                )
            if stats.get("janitoignore_ignored", 0) > 0:
                ignore_filters.append(
                    f".janitoignore filtered {stats['janitoignore_ignored']} items"
                )
            if ignore_filters:
                print("-" * 40)
                print(f"({', '.join(ignore_filters)})")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
