#!/usr/bin/env python3
"""
Remove Directory Tool - A class-based tool for removing directories.

This tool demonstrates how to use the base tool class with progress reporting.
It provides safe directory removal with options for recursive deletion.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.remove_directory [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
import shutil
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool


def _count_items(abs_directory: str) -> int:
    """Count the entries under ``abs_directory`` (excluding the root itself)."""
    count = 0
    for root, dirs, files in os.walk(abs_directory):
        count += len(dirs) + len(files)
    return count


@tool(permissions="w")
class RemoveDirectory(BaseTool):
    """
    Tool for removing a directory from the filesystem.
    """

    def _validate_target(
        self,
        abs_directory: str,
        norm_path_str: str,
        directory: str,
        recursive: bool,
        force: bool,
    ) -> dict[str, Any] | None:
        """Return a result dict when the target is missing/not a directory, else None."""
        if not os.path.exists(abs_directory):
            if force:
                message = (
                    f"Directory does not exist (ignored due to force=True): "
                    f"{norm_path_str}"
                )
                self.report_result(message)
                return {
                    "success": True,
                    "directory": directory,
                    "message": message,
                    "recursive": recursive,
                    "force": force,
                    "items_removed": 0,
                }
            self.report_error(f"Directory does not exist: {norm_path_str}")
            return {
                "success": False,
                "error": f"Directory does not exist: {norm_path_str}",
                "directory": directory,
                "recursive": recursive,
                "force": force,
            }

        if not os.path.isdir(abs_directory):
            if force:
                message = (
                    f"Path is not a directory (ignored due to force=True): "
                    f"{norm_path_str}"
                )
                self.report_result(message)
                return {
                    "success": True,
                    "directory": directory,
                    "message": message,
                    "recursive": recursive,
                    "force": force,
                    "items_removed": 0,
                }
            self.report_error(f"Path is not a directory: {norm_path_str}")
            return {
                "success": False,
                "error": f"Path is not a directory: {norm_path_str}",
                "directory": directory,
                "recursive": recursive,
                "force": force,
            }

        return None

    def _remove_recursive(
        self, abs_directory: str, norm_path_str: str, force: bool
    ) -> tuple[str, int]:
        """Remove a directory recursively; returns (message, items_removed)."""
        items_removed = _count_items(abs_directory)
        size_str = f"({items_removed} items)"
        self.report_progress(f" {size_str}", end="")

        try:
            # Remove recursively
            shutil.rmtree(abs_directory)
            return (
                f"Successfully removed directory recursively {norm_path_str}",
                items_removed,
            )
        except Exception as e:
            if not force:
                raise e
            # Try alternative removal methods or just report and continue
            self.report_warning(
                f"Partial removal completed, some items may remain: {e!s}"
            )
            return (
                f"Partially removed directory {norm_path_str} (force mode)",
                items_removed,
            )

    def _remove_non_recursive(
        self,
        abs_directory: str,
        norm_path_str: str,
        force: bool,
        directory: str,
        recursive: bool,
    ):
        """Remove an empty directory; returns (message, items_removed) or an error dict."""
        try:
            os.rmdir(abs_directory)
            return f"Successfully removed empty directory {norm_path_str}", 0
        except OSError as e:
            if e.errno != 39:  # Directory not empty
                raise e

            if not force:
                self.report_error(
                    f"Directory not empty: {norm_path_str}"
                    f" (use recursive=True to remove"
                    f" non-empty directories)"
                )
                return {
                    "success": False,
                    "error": (
                        f"Directory not empty: {norm_path_str}"
                        f" (use recursive=True to remove"
                        f" non-empty directories)"
                    ),
                    "directory": directory,
                    "recursive": recursive,
                    "force": force,
                }

            self.report_warning(
                "Directory not empty, attempting recursive removal (force mode)"
            )
            # Count items before removal
            items_removed = _count_items(abs_directory)
            size_str = f"({items_removed} items)"
            self.report_progress(f" {size_str}", end="")
            shutil.rmtree(abs_directory)
            message = (
                f"Successfully removed directory"
                f" recursively {norm_path_str}"
                f" (force mode)"
            )
            return message, items_removed

    def run(
        self, directory: str, recursive: bool = False, force: bool = False
    ) -> dict[str, Any]:
        """
        Remove a directory from the filesystem.

        Args:
            directory (str): The path to the directory to remove
            recursive (bool): Whether to remove directory and all its contents recursively (default: False)
            force (bool): Whether to ignore errors and continue (default: False)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'directory': the directory that was removed
                - 'message': success message with details
                - 'recursive': whether recursive removal was used
                - 'items_removed': number of items removed (if recursive=True)
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_directory = os.path.abspath(directory)
            norm_path_str = norm_path(abs_directory)

            # Report start
            recursive_str = "recursively" if recursive else ""
            self.report_start(
                f"\U0001f5d1\ufe0f Removing directory {norm_path_str} {recursive_str}",
                end="",
            )

            # Validate the target exists and is a directory
            validation = self._validate_target(
                abs_directory, norm_path_str, directory, recursive, force
            )
            if validation is not None:
                return validation

            # Count items if recursive
            items_removed = 0
            if recursive:
                message, items_removed = self._remove_recursive(
                    abs_directory, norm_path_str, force
                )
            else:
                # Non-recursive removal (only empty directories)
                result = self._remove_non_recursive(
                    abs_directory, norm_path_str, force, directory, recursive
                )
                if isinstance(result, dict):
                    return result  # error result
                message, items_removed = result

            self.report_result(message)

            return {
                "success": True,
                "directory": directory,
                "message": message,
                "recursive": recursive,
                "force": force,
                "items_removed": items_removed,
            }

        except PermissionError as e:
            self.report_error(f"Permission denied: {e!s}")
            return {
                "success": False,
                "error": f"Permission denied: {e!s}",
                "directory": directory,
                "recursive": recursive,
                "force": force,
            }
        except OSError as e:
            self.report_error(f"OS Error removing directory: {e!s}")
            return {
                "success": False,
                "error": f"OS Error removing directory: {e!s}",
                "directory": directory,
                "recursive": recursive,
                "force": force,
            }
        except Exception as e:
            self.report_error(f"Error removing directory: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "directory": directory,
                "recursive": recursive,
                "force": force,
            }


# CLI interface for testing
def main():
    """Command line interface for testing the RemoveDirectoryTool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove directory tool for AI function calling"
    )
    parser.add_argument("directory", help="Directory path to remove")
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Remove directory and all contents recursively",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force removal, ignore errors"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    tool_instance = RemoveDirectory()
    result = tool_instance.run(
        directory=args.directory, recursive=args.recursive, force=args.force
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
