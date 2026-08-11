#!/usr/bin/env python3
"""
RunGitHubCLI Tool - Executes the GitHub CLI (`gh`) to interact with GitHub artifacts.

The tool streams command output in real-time (like RunBashCode) and returns
the captured stdout/stderr along with the exit code.  It is only loaded when
the `gh` executable is found on PATH (or in well-known install locations),
so agents running without the GitHub CLI installed will never see this tool.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.run_github_cli [args]
For AI function calling, use through the tool registry (tooling.tools_registry).

WARNING: This tool executes the GitHub CLI and can modify remote repositories,
issues, pull requests, releases, and other GitHub artifacts. Use with caution.
"""

import json
import os
import shutil
import sys
import time
from typing import Any

from ...tooling import BaseTool, format_duration_ms
from ...tooling.decorator import tool
from ._output_capture import OutputCapture, build_report_message, print_stored_files
from ._streaming import stream_execute

# Candidate executable names for the GitHub CLI.
_GH_CANDIDATES = ("gh", "gh.exe")


def _well_known_gh_paths() -> list[str]:
    """
    Build a list of well-known ``gh`` install locations.

    These are probed as a fallback when ``gh`` is not found on PATH.
    Only paths that actually exist and are executable will be accepted by
    the caller.
    """
    paths: list[str] = []

    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        paths.extend(
            [
                os.path.join(program_files, "GitHub CLI", "gh.exe"),
                os.path.join(program_files, "GitHub", "gh.exe"),
            ]
        )
        if local_app_data:
            paths.append(
                os.path.join(local_app_data, "Programs", "GitHub CLI", "gh.exe")
            )
    elif sys.platform == "darwin":
        paths.extend(
            [
                "/usr/local/bin/gh",  # Homebrew (Intel)
                "/opt/homebrew/bin/gh",  # Homebrew (Apple Silicon)
                "/opt/local/bin/gh",  # MacPorts
            ]
        )
    else:  # Linux and other POSIX
        paths.extend(
            [
                "/usr/bin/gh",
                "/usr/local/bin/gh",
                "/snap/bin/gh",  # Snap (Ubuntu)
            ]
        )

    return paths


@tool(permissions="x")
class RunGitHubCLI(BaseTool):
    """
    Tool for executing the GitHub CLI (`gh`) to interact with GitHub artifacts.

    This tool is only available when the `gh` command-line client is installed.
    It runs the supplied command line through `gh`, streams the output in
    real-time, and returns the captured stdout, stderr, and exit code.

    Examples of commands:
        - "repo list"            — list repositories for the authenticated user
        - "issue list -R owner/repo"  — list issues in a repository
        - "pr view 42"           — view pull request #42
        - "api repos/{owner}/{repo}" — call the GitHub API directly

    Security Notes:
    - Only execute trusted `gh` commands
    - Be cautious with commands that mutate state (e.g. `gh pr merge`)
    - The CLI uses whatever credentials are configured via `gh auth`
    """

    # Cached result of executable detection (None = not found or not checked yet)
    _gh_path: str | None = None
    _gh_checked: bool = False

    @classmethod
    def _find_gh(cls) -> str | None:
        """
        Locate the ``gh`` executable.

        PATH is searched first, then well-known install locations.
        The result is cached on the class for subsequent calls.

        Returns:
            Optional[str]: Absolute path to the executable, or None if not found.
        """
        if cls._gh_checked:
            return cls._gh_path
        cls._gh_checked = True
        cls._gh_path = None

        # 1) Search PATH
        for name in _GH_CANDIDATES:
            path = shutil.which(name)
            if path:
                cls._gh_path = path
                return path

        # 2) Probe well-known install locations
        for path in _well_known_gh_paths():
            if os.path.isfile(path) and os.access(path, os.X_OK):
                cls._gh_path = path
                return path

        return None

    @classmethod
    def should_load(cls) -> bool:
        """
        Only load this tool if the GitHub CLI (`gh`) is available.

        Returns:
            bool: True if `gh` is found, False otherwise.
        """
        if cls._find_gh() is None:
            cls._load_skip_reason = (
                "GitHub CLI ('gh') not found — looked on PATH and in "
                "well-known install locations. Install it from "
                "https://cli.github.com/ to enable this tool."
            )
            return False
        return True

    def run(self, cmdline: str) -> dict[str, Any]:
        """
        Execute a GitHub CLI command and return the results.

        The *cmdline* string is everything that follows ``gh``.  For example,
        pass ``"repo list"`` to run ``gh repo list``.

        Args:
            cmdline (str): The command line arguments to pass to `gh`
                (e.g. "repo list --limit 5").  Do NOT include the leading
                "gh" — it is prepended automatically.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool — True if the exit code was 0
                - 'exit_code': int — process exit code
                - 'stdout': str — captured standard output
                - 'stderr': str — captured standard error
                - 'command': str — the full command that was executed
                - 'gh_executable': str — path to the gh binary used
                - 'execution_time_ms': int — wall-clock time in milliseconds
                - 'error': str — error message (only present when success is False)
        """
        start_time = time.time()

        gh_path = self._find_gh()
        if gh_path is None:
            self.report_error("GitHub CLI not found")
            return {
                "success": False,
                "error": (
                    "GitHub CLI ('gh') not found. Install it from https://cli.github.com/ and ensure it is on PATH."
                ),
                "exit_code": -1,
                "command": cmdline,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        try:
            full_command = f"{gh_path} {cmdline}"
            self._report_exec_start(cmdline)
            shell_command = self._build_shell_command(full_command)

            stdout_capture = OutputCapture("stdout")
            stderr_capture = OutputCapture("stderr")

            def _tee(stream_name: str, line: str) -> None:
                if stream_name == "stdout":
                    stdout_capture.add(line)
                elif stream_name == "stderr":
                    stderr_capture.add(line)

            exit_code, stdout_lines, stderr_lines, execution_time_ms = stream_execute(
                shell_command,
                os.getcwd(),
                True,
                True,
                120,  # generous default for network-bound gh commands
                start_time,
                self.report_output,
                report_blank_first=True,
                tee=_tee,
                popen_kwargs={
                    "encoding": "utf-8",
                    "errors": "replace",
                    "env": {**os.environ},
                },
            )

            return self._build_result(
                exit_code,
                cmdline,
                gh_path,
                stdout_capture,
                stderr_capture,
                execution_time_ms,
            )
        except FileNotFoundError:
            self.report_error("gh executable not found at runtime")
            return {
                "success": False,
                "error": f"gh executable not found at: {gh_path}",
                "exit_code": -1,
                "command": f"gh {cmdline}",
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to execute gh: {e!s}",
                "exit_code": -1,
                "command": f"gh {cmdline}",
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    def _report_exec_start(self, cmdline: str) -> None:
        """Report the command to be executed."""
        code_preview = cmdline
        if len(code_preview) > 200:
            code_preview = code_preview[:200] + "..."
        self.report_start(f"⚙️ Executing: gh {code_preview}")

    def _build_shell_command(self, full_command: str) -> list[str] | str:
        """Resolve a shell to run the command through (prefer bash, fall back to sh)."""
        shell_exe = shutil.which("bash") or shutil.which("sh")
        if shell_exe:
            return [shell_exe, "-c", full_command]
        # Extremely unlikely (we already found gh), but be safe.
        return full_command

    def _build_result(
        self,
        exit_code: int,
        cmdline: str,
        gh_path: str,
        stdout_capture: OutputCapture,
        stderr_capture: OutputCapture,
        execution_time_ms: int,
    ) -> dict[str, Any]:
        """Assemble the result dict and report the outcome.

        stdout/stderr are capped at ``MAX_OUTPUT_LINES``; when a stream is
        longer, the full output lives in a kept temp file referenced by the
        ``stdout_file`` / ``stderr_file`` keys (issue #49).
        """
        stdout_str, stdout_file = stdout_capture.finalize()
        stderr_str, stderr_file = stderr_capture.finalize()
        success = exit_code == 0

        result: dict[str, Any] = {
            "success": success,
            "exit_code": exit_code if exit_code is not None else -1,
            "command": f"gh {cmdline}",
            "gh_executable": gh_path,
            "execution_time_ms": execution_time_ms,
            "stdout": stdout_str,
            "stderr": stderr_str,
        }
        if stdout_file:
            result["stdout_file"] = stdout_file
        if stderr_file:
            result["stderr_file"] = stderr_file

        if success:
            self._report_success(execution_time_ms, stdout_capture, stderr_capture)
        else:
            self._report_failure(exit_code, stderr_capture, stdout_capture)
            result["error"] = f"gh exited with code {exit_code}"
        return result

    def _report_success(
        self,
        execution_time_ms: int,
        stdout_capture: OutputCapture,
        stderr_capture: OutputCapture,
    ) -> None:
        """Report a successful execution summary."""
        summary = f"Completed in {format_duration_ms(execution_time_ms)}"
        if stdout_capture.line_count():
            summary += f" ({stdout_capture.line_count()} lines output)"
        stored = build_report_message(
            stdout_capture.file_path, stderr_capture.file_path
        )
        if stored:
            summary += f" — {stored}"
        self.report_result(summary)

    def _report_failure(
        self,
        exit_code: int,
        stderr_capture: OutputCapture,
        stdout_capture: OutputCapture,
    ) -> None:
        """Report a failed execution, truncating long stderr previews."""
        error_msg = f"Exit code {exit_code}"
        if stderr_capture.line_count():
            stderr_preview = stderr_capture.preview(200)
            error_msg += f": {stderr_preview}"
        stored = build_report_message(
            stdout_capture.file_path, stderr_capture.file_path
        )
        if stored:
            error_msg += f" — {stored}"
        self.report_error(error_msg)


# ── CLI testing harness ─────────────────────────────────────────────────────
def main():
    """Command line interface for testing the RunGitHubCLI tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute a GitHub CLI command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "repo list --limit 5"
  %(prog)s "issue list -R cli/cli"
  %(prog)s "pr view 42 -R owner/repo"
  %(prog)s "api repos/cli/cli" --json
        """,
    )
    parser.add_argument(
        "cmdline",
        help="Arguments to pass to gh (e.g. 'repo list --limit 5')",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output result as JSON"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )

    args = parser.parse_args()

    tool_instance = RunGitHubCLI()
    result = tool_instance.run(cmdline=args.cmdline)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✓ gh execution successful (exit code {result['exit_code']})")
            print(
                f"  Execution time: {format_duration_ms(result['execution_time_ms'])}"
            )
            if args.verbose:
                print(f"  Executable: {result.get('gh_executable', 'unknown')}")
                print(f"  Command: {result['command']}")
            if result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])
            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])
            print_stored_files(result)
        else:
            print("✗ gh execution failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Exit code: {result['exit_code']}")
            if args.verbose and result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])
            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])
            print_stored_files(result)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
