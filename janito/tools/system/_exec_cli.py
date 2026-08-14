"""
Shared CLI testing harness for the exec tools (Bash / PowerShell).

Extracted from ``run_bash_code.py`` and ``run_powershell_code.py`` so both
tool modules stay focused on the ``BaseTool`` class implementation and the
standalone ``python -m janito.tools.system.<tool>`` entry point stays
available.
"""

import json
import os
from typing import Any

from ...tooling import format_duration_ms, norm_path
from ._output_capture import print_stored_files


def run_cli(
    tool_cls,
    *,
    tool_name: str,
    description: str,
    epilog: str,
    code_help: str,
    file_help: str,
    result_key: str,
    extra_run_kwargs: dict[str, Any] | None = None,
    add_shell_arg: bool = False,
    shell_help: str | None = None,
) -> int:
    """Run the shared argparse-based CLI harness for an exec tool.

    Args:
        tool_cls: The ``BaseTool`` subclass to instantiate.
        tool_name: Display name for messages (e.g. ``"Bash"``).
        description: argparse description.
        epilog: argparse epilog with examples.
        code_help: Help text for ``-c/--code``.
        file_help: Help text for ``-f/--file``.
        result_key: Result dict key for the executable path
            (e.g. ``"bash_executable"``).
        extra_run_kwargs: Extra keyword arguments forwarded to ``run()``.
        add_shell_arg: Whether to add a ``-s/--shell`` argument.
        shell_help: Help text for ``-s/--shell`` (only when ``add_shell_arg``).
    """
    parser = _build_parser(
        description=description,
        epilog=epilog,
        code_help=code_help,
        file_help=file_help,
        add_shell_arg=add_shell_arg,
        shell_help=shell_help,
    )
    args = parser.parse_args()
    code = _read_code(args, parser)
    if code is None:
        return 1

    run_kwargs = {
        "code": code,
        "working_directory": args.directory,
        "timeout": args.timeout,
        "capture_output": not args.no_capture_output,
        "capture_errors": not args.no_capture_errors,
    }
    if add_shell_arg:
        run_kwargs["bash_executable"] = args.shell
    if extra_run_kwargs:
        run_kwargs.update(extra_run_kwargs)

    tool_instance = tool_cls()
    result = tool_instance.run(**run_kwargs)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_result(result, args, tool_name, result_key)
    return 0 if result["success"] else 1


def _build_parser(
    *,
    description: str,
    epilog: str,
    code_help: str,
    file_help: str,
    add_shell_arg: bool,
    shell_help: str | None,
):
    """Build the CLI argument parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    parser.add_argument("-c", "--code", help=code_help)
    parser.add_argument("-f", "--file", help=file_help)
    parser.add_argument("-d", "--directory", help="Working directory for execution")
    if add_shell_arg:
        parser.add_argument("-s", "--shell", help=shell_help)
    parser.add_argument(
        "-t", "--timeout", type=int, default=60, help="Timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--no-capture-output", action="store_true", help="Don't capture standard output"
    )
    parser.add_argument(
        "--no-capture-errors", action="store_true", help="Don't capture standard error"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )
    return parser


def _read_code(args, parser) -> str | None:
    """Resolve the code from --code/--file; return None on file errors."""
    if not args.code and not args.file:
        parser.error("Either --code or --file must be specified")

    if args.code and args.file:
        parser.error("Cannot specify both --code and --file")

    code = args.code
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            return None
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    return code


def _print_result(
    result: dict[str, Any], args, tool_name: str, result_key: str
) -> None:
    """Pretty-print the tool result."""
    if result["success"]:
        print(
            f"\u2713 {tool_name} execution successful (exit code {result['exit_code']})"
        )
        print(f"  Working directory: {norm_path(result['working_directory'])}")
        print(f"  Execution time: {format_duration_ms(result['execution_time_ms'])}")

        if args.verbose:
            print(f"  Executable: {result.get(result_key, 'unknown')}")
            print("\nCommand:")
            print(f"  {result['command']}")

        if result.get("stdout"):
            print("\nOutput:")
            print(result["stdout"])

        if result.get("stderr"):
            print("\nStderr:")
            print(result["stderr"])

        print_stored_files(result)
    else:
        print(f"\u2717 {tool_name} execution failed")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        print(f"  Exit code: {result['exit_code']}")

        if args.verbose:
            print("\nCommand:")
            print(f"  {result['command']}")

        if result.get("stdout"):
            print("\nOutput:")
            print(result["stdout"])

        if result.get("stderr"):
            print("\nStderr:")
            print(result["stderr"])

        print_stored_files(result)
