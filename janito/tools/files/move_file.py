#!/usr/bin/env python3
"""
Move File Tool - A class-based tool for moving and renaming files and directories.

This tool demonstrates how to use the base tool class with progress reporting.
It provides cross-platform file moving with safety features and metadata preservation.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.move_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
import platform
import shutil
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool


def _determine_operation(
    source_dir: str, dest_dir: str, source_name: str, dest_name: str
) -> str:
    """Classify the move as ``move``/``rename``/``move_rename``."""
    if source_dir == dest_dir:
        if source_name == dest_name:
            return "move"  # Same directory, same name (shouldn't happen due to earlier check)
        return "rename"
    if source_name == dest_name:
        return "move"
    return "move_rename"


def _capture_metadata(abs_source: str) -> dict | None:
    """Capture timestamps/permissions of a file before moving (best effort)."""
    try:
        metadata = {
            "st_atime": os.path.getatime(abs_source),
            "st_mtime": os.path.getmtime(abs_source),
            "st_mode": os.stat(abs_source).st_mode,
        }
        if hasattr(os.stat(abs_source), "st_uid"):
            metadata["st_uid"] = os.stat(abs_source).st_uid
            metadata["st_gid"] = os.stat(abs_source).st_gid
        return metadata
    except Exception:
        return None


def _restore_metadata(abs_destination: str, metadata: dict) -> None:
    """Restore timestamps/permissions after moving (best effort)."""
    try:
        # Restore timestamps
        os.utime(
            abs_destination,
            (metadata["st_atime"], metadata["st_mtime"]),
        )
        # Restore permissions on Unix
        if platform.system() != "Windows" and "st_mode" in metadata:
            os.chmod(abs_destination, metadata["st_mode"])
    except Exception:
        pass  # Metadata preservation is best effort


@tool(permissions="rw")
class MoveFile(BaseTool):
    """
    Tool for moving or renaming files and directories.
    """

    def _create_parent_dirs(self, abs_destination: str, create_dirs: bool) -> list:
        """Create the destination parent dirs when requested; returns created dirs."""
        created_dirs = []
        dest_parent = os.path.dirname(abs_destination)
        if create_dirs and dest_parent and not os.path.exists(dest_parent):
            os.makedirs(dest_parent, exist_ok=True)
            created_dirs.append(norm_path(dest_parent))
            self.report_progress(" (created directories)", end="")
        return created_dirs

    @staticmethod
    def _build_success_message(
        operation: str, is_directory: bool, overwritten: bool
    ) -> str:
        """Build the human-readable success message."""
        item_type = "directory" if is_directory else "file"

        if operation == "rename":
            action = f"renamed {item_type}"
        elif operation == "move":
            action = f"moved {item_type}"
        else:
            action = f"moved and renamed {item_type}"

        message = f"Successfully {action}"
        if overwritten:
            message += " (overwritten)"
        return message

    def _move_entry(
        self,
        abs_source: str,
        abs_destination: str,
        is_directory: bool,
        original_metadata: dict | None,
        preserve_metadata: bool,
    ) -> None:
        """Move the entry, restoring metadata afterwards for files."""
        if is_directory:
            # For directories, use shutil.move which handles cross-device moves
            shutil.move(abs_source, abs_destination)
        else:
            # For files, use shutil.move for atomicity and cross-device support
            shutil.move(abs_source, abs_destination)

            # Restore metadata if requested
            if preserve_metadata and original_metadata:
                _restore_metadata(abs_destination, original_metadata)

    def _do_move(
        self,
        source: str,
        destination: str,
        overwrite: bool,
        create_dirs: bool,
        preserve_metadata: bool,
    ) -> dict[str, Any]:
        """Validate and perform the move; returns the result dict."""
        abs_source = os.path.abspath(source)
        abs_destination = os.path.abspath(destination)
        norm_source = norm_path(abs_source)
        norm_dest = norm_path(abs_destination)

        # Report start
        self.report_start(f"\U0001f4e6 Moving {norm_source} to {norm_dest}...", end="")

        # Validate source exists
        if not os.path.exists(abs_source):
            self.report_error(f"Source does not exist: {norm_source}")
            return {
                "success": False,
                "error": f"Source does not exist: {norm_source}",
                "source": source,
            }

        # Check if source and destination are the same
        if abs_source == abs_destination:
            self.report_error(f"Source and destination are the same: {norm_source}")
            return {
                "success": False,
                "error": f"Source and destination are the same: {norm_source}",
                "source": source,
                "destination": destination,
            }

        # Check if destination already exists
        overwritten = False
        if os.path.exists(abs_destination):
            if not overwrite:
                self.report_error(
                    f"Destination already exists: {norm_dest} (use overwrite=True to replace)"
                )
                return {
                    "success": False,
                    "error": f"Destination already exists: {norm_dest} (use overwrite=True to replace)",
                    "source": source,
                    "destination": destination,
                }
            overwritten = True
            self.report_progress(" (will overwrite)", end="")

        # Create parent directories if requested
        created_dirs = self._create_parent_dirs(abs_destination, create_dirs)

        # Determine operation type
        operation = _determine_operation(
            os.path.dirname(abs_source),
            os.path.dirname(abs_destination),
            os.path.basename(abs_source),
            os.path.basename(abs_destination),
        )

        # Check if moving directory
        is_directory = os.path.isdir(abs_source)

        # Preserve original metadata if requested
        original_metadata = None
        if preserve_metadata and not is_directory:
            original_metadata = _capture_metadata(abs_source)

        # Perform the move operation
        self._move_entry(
            abs_source,
            abs_destination,
            is_directory,
            original_metadata,
            preserve_metadata,
        )

        # Build success message
        message = self._build_success_message(operation, is_directory, overwritten)
        self.report_result(message)

        return {
            "success": True,
            "source": source,
            "destination": destination,
            "operation": operation,
            "overwritten": overwritten,
            "created_dirs": created_dirs,
            "metadata_preserved": preserve_metadata and not is_directory,
            "is_directory": is_directory,
            "message": message,
        }

    def run(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
        create_dirs: bool = False,
        preserve_metadata: bool = True,
    ) -> dict[str, Any]:
        """
        Move or rename a file or directory from source to destination.

        Args:
            source (str): Source file or directory path
            destination (str): Destination path
            overwrite (bool): Allow overwriting existing files (default: False)
            create_dirs (bool): Create parent directories if missing (default: False)
            preserve_metadata (bool): Preserve timestamps and permissions (default: True)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'source': the source path
                - 'destination': the destination path
                - 'operation': 'move' or 'rename' or 'move_rename'
                - 'overwritten': whether an existing file was overwritten
                - 'created_dirs': list of directories created
                - 'metadata_preserved': whether metadata was preserved
                - 'is_directory': whether a directory was moved
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            return self._do_move(
                source, destination, overwrite, create_dirs, preserve_metadata
            )
        except PermissionError as e:
            self.report_error(f"Permission denied: {e!s}")
            return {
                "success": False,
                "error": f"Permission denied: {e!s}",
                "source": source,
                "destination": destination,
            }
        except OSError as e:
            if e.errno == 18:  # Cross-device link error
                self.report_error(f"Cross-device move failed: {e!s}")
                return {
                    "success": False,
                    "error": f"Cross-device move failed: {e!s}",
                    "source": source,
                    "destination": destination,
                }
            self.report_error(f"OS Error: {e!s}")
            return {
                "success": False,
                "error": f"OS Error: {e!s}",
                "source": source,
                "destination": destination,
            }
        except Exception as e:
            self.report_error(f"Error moving file: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "source": source,
                "destination": destination,
            }


# CLI interface for testing
def main():
    """Command line interface for testing the MoveFile tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Move file tool for AI function calling"
    )
    parser.add_argument("source", help="Source file or directory path")
    parser.add_argument("destination", help="Destination path")
    parser.add_argument(
        "--overwrite", "-o", action="store_true", help="Overwrite existing destination"
    )
    parser.add_argument(
        "--create-dirs",
        "-c",
        action="store_true",
        help="Create parent directories if missing",
    )
    parser.add_argument(
        "--no-preserve-metadata",
        action="store_true",
        help="Don't preserve file metadata",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    tool_instance = MoveFile()
    result = tool_instance.run(
        source=args.source,
        destination=args.destination,
        overwrite=args.overwrite,
        create_dirs=args.create_dirs,
        preserve_metadata=not args.no_preserve_metadata,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(result["message"])
            print(f"  From: {norm_path(result['source'])}")
            print(f"  To:   {norm_path(result['destination'])}")
            if result.get("created_dirs"):
                print(f"  Created directories: {', '.join(result['created_dirs'])}")
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
