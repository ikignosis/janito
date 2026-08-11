#!/usr/bin/env python3
"""
Read File Tool - A class-based tool for reading file contents.

This tool demonstrates how to use the base tool class with progress reporting.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.files.read_file [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
from typing import Any

from ...tooling import BaseTool, norm_path
from ...tooling.decorator import tool

# Number of lines returned by the head/tail flags.
_HEAD_TAIL_LINES = 10


@tool(permissions="r")
class ReadFile(BaseTool):
    """
    Tool for reading the contents of a file.

    Args:
        filepath (str): Path to the file to read
        start_line (int): Starting line number (1-based). Defaults to 1.
        max_lines (int, optional): Maximum number of lines to read from
            start_line. Defaults to None (read to end of file).
        head (bool): If True, return only the first 10 lines of the file.
        tail (bool): If True, return only the last 10 lines of the file.
    """

    def run(
        self,
        filepath: str,
        start_line: int = 1,
        max_lines: int | None = None,
        head: bool = False,
        tail: bool = False,
    ) -> dict[str, Any]:
        """
        Read the contents of a file.

        Args:
            filepath (str): The path to the file to read
            start_line (int): Starting line number (1-based). Defaults to 1.
            max_lines (int, optional): Maximum number of lines to read,
                starting from ``start_line``. If None, reads to the end of the
                file. Values beyond the end of the file are clamped to the
                last line, so the tool returns all the lines it could read.
            head (bool): If True, return only the first 10 lines of the file.
                Takes precedence over ``start_line``/``max_lines``.
            tail (bool): If True, return only the last 10 lines of the file.
                Takes precedence over ``start_line``/``max_lines``.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'content': file content as string (if successful)
                - 'filepath': the file that was read
                - 'start_line': first line actually returned (1-based)
                - 'max_lines': effective line limit (None means no limit)
                - 'total_lines': total number of lines in the file
                - 'lines_read': number of lines actually read
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            abs_filepath = os.path.abspath(filepath)
            norm_path_str = norm_path(abs_filepath)

            # Report start
            range_info = ""
            if head:
                range_info = f" (first {_HEAD_TAIL_LINES} lines)"
            elif tail:
                range_info = f" (last {_HEAD_TAIL_LINES} lines)"
            elif max_lines is not None:
                range_info = f" (start at line {start_line}, max {max_lines} lines)"
            else:
                range_info = f" (start at line {start_line}, until EOF)"

            self.report_start(
                f"\U0001f4d6 Reading file {norm_path_str}{range_info}", end=""
            )

            if not os.path.exists(abs_filepath):
                self.report_error(f"File does not exist: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"File does not exist: {norm_path_str}",
                    "filepath": filepath,
                }

            if not os.path.isfile(abs_filepath):
                self.report_error(f"Path is not a file: {norm_path_str}")
                return {
                    "success": False,
                    "error": f"Path is not a file: {norm_path_str}",
                    "filepath": filepath,
                }

            # Get file size for progress indication
            file_size = os.path.getsize(abs_filepath)
            size_str = f"({file_size} bytes)"
            self.report_progress(f" {size_str}", end="")

            # Read the file and determine total lines
            with open(abs_filepath, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)

            try:
                actual_from, effective_max = self._resolve_slice(
                    start_line, max_lines, head, tail, total_lines
                )
            except ValueError as e:
                error_msg = str(e)
                self.report_error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "filepath": filepath,
                    "total_lines": total_lines,
                }

            # A max_lines beyond the end of the file is not an error: clamp it
            # to the last available line so the caller gets all the lines the
            # tool could read instead of a failure.
            actual_to = (
                min(actual_from + effective_max, total_lines)
                if effective_max is not None
                else total_lines
            )

            # Extract the requested lines
            selected_lines = all_lines[actual_from:actual_to]
            content = "".join(selected_lines)
            lines_read = len(selected_lines)

            # Determine actual line range read
            actual_from_line = actual_from + 1  # Convert back to 1-based
            actual_to_line = actual_from + lines_read  # 1-based end line

            self.report_result(
                f"Read {lines_read} lines (lines {actual_from_line}-{actual_to_line})"
            )

            return {
                "success": True,
                "content": content,
                "filepath": filepath,
                "start_line": actual_from_line,
                "max_lines": effective_max,
                "total_lines": total_lines,
                "lines_read": lines_read,
            }

        except Exception as e:
            self.report_error(f"Error reading file: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "filepath": filepath,
                "start_line": start_line,
                "max_lines": max_lines,
            }

    @staticmethod
    def _resolve_slice(
        start_line: int,
        max_lines: int | None,
        head: bool,
        tail: bool,
        total_lines: int,
    ) -> tuple[int, int | None]:
        """
        Resolve the slice to read as (0-based start line, line limit).

        ``head``/``tail`` take precedence over ``start_line``/``max_lines``.

        Args:
            start_line: Requested 1-based start line.
            max_lines: Requested line limit (None = read to end of file).
            head: If True, read only the first 10 lines.
            tail: If True, read only the last 10 lines.
            total_lines: Number of lines in the file.

        Returns:
            tuple[int, int | None]: (0-based start line, line limit). A line
            limit of None means "read to end of file".

        Raises:
            ValueError: if the arguments are invalid.
        """
        if head and tail:
            raise ValueError("head and tail cannot both be True")

        if head:
            return 0, _HEAD_TAIL_LINES

        if tail:
            return max(total_lines - _HEAD_TAIL_LINES, 0), _HEAD_TAIL_LINES

        if start_line < 1 or start_line > total_lines:
            raise ValueError(
                f"start_line ({start_line}) is out of range. "
                f"File has {total_lines} lines."
            )

        if max_lines is not None and max_lines < 1:
            raise ValueError(
                f"max_lines ({max_lines}) is out of range. "
                "max_lines must be at least 1."
            )

        return start_line - 1, max_lines


# CLI interface for testing
def main():
    """Command line interface for testing the ReadFileTool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Read file tool for AI function calling"
    )
    parser.add_argument("filepath", help="File path to read")
    parser.add_argument(
        "--start-line",
        "-s",
        type=int,
        default=1,
        help="Starting line number (1-based, default: 1)",
    )
    parser.add_argument(
        "--max-lines",
        "-m",
        type=int,
        default=None,
        help="Maximum number of lines to read (default: end of file)",
    )
    parser.add_argument(
        "--head",
        action="store_true",
        help="Return only the first 10 lines of the file",
    )
    parser.add_argument(
        "--tail",
        action="store_true",
        help="Return only the last 10 lines of the file",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    tool_instance = ReadFile()
    result = tool_instance.run(
        filepath=args.filepath,
        start_line=args.start_line,
        max_lines=args.max_lines,
        head=args.head,
        tail=args.tail,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            norm_path_str = norm_path(result["filepath"])
            start_line = result.get("start_line", 1)
            lines_read = result.get("lines_read", 0)
            end_line = start_line + lines_read - 1
            print(f"Content of '{norm_path_str}' (lines {start_line}-{end_line}):")
            print("-" * 40)
            print(result["content"])
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
