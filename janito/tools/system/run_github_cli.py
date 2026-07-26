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
import subprocess
import sys
import time
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool

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
                    "GitHub CLI ('gh') not found. Install it from "
                    "https://cli.github.com/ and ensure it is on PATH."
                ),
                "exit_code": -1,
                "command": cmdline,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        try:
            # Build the full command: gh <cmdline>
            # We invoke through the shell so users can pass pipelines,
            # quoting, and other shell constructs naturally.
            full_command = f"{gh_path} {cmdline}"

            code_preview = cmdline
            if len(code_preview) > 200:
                code_preview = code_preview[:200] + "..."
            self.report_start(f"⚙️ Executing: gh {code_preview}")

            # ── Real-time streaming (same pattern as RunBashCode) ──
            import queue
            import threading

            captured_stdout: list[str] = []
            captured_stderr: list[str] = []

            # Resolve a shell to run the command through (prefer bash, fall
            # back to sh).  We do NOT hardcode a shell name because the
            # platform may vary.
            shell_exe = shutil.which("bash") or shutil.which("sh")
            if shell_exe:
                shell_command = [shell_exe, "-c", full_command]
            else:
                # Extremely unlikely (we already found gh), but be safe.
                shell_command = full_command  # type: ignore[assignment]

            process = subprocess.Popen(
                shell_command,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                env={**os.environ},
            )

            output_queue: queue.Queue[tuple[str, str]] = queue.Queue()

            def read_stream(
                stream: Any, stream_name: str, capture_list: list[str]
            ) -> None:
                """Read lines from *stream* and enqueue them."""
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            output_queue.put((stream_name, line.rstrip("\r\n")))
                            capture_list.append(line)
                    stream.close()
                except Exception as e:  # pragma: no cover
                    output_queue.put(("error", f"Error reading {stream_name}: {e}"))

            threads: list[threading.Thread] = []
            if process.stdout:
                t = threading.Thread(
                    target=read_stream,
                    args=(process.stdout, "stdout", captured_stdout),
                    daemon=True,
                )
                t.start()
                threads.append(t)
            if process.stderr:
                t = threading.Thread(
                    target=read_stream,
                    args=(process.stderr, "stderr", captured_stderr),
                    daemon=True,
                )
                t.start()
                threads.append(t)

            # ── Monitor loop ──
            exit_code: int | None = None
            displayed_any_output = False
            timeout = 120  # generous default for network-bound gh commands

            while True:
                exit_code = process.poll()
                process_finished = exit_code is not None

                # Drain the queue
                try:
                    while True:
                        stream_name, line = output_queue.get_nowait()
                        if stream_name in ("stdout", "stderr"):
                            if not displayed_any_output:
                                self.report_output("")
                                displayed_any_output = True
                            self.report_output(line)
                        elif stream_name == "error":
                            self.report_output(f"STREAM ERROR: {line}")
                except queue.Empty:
                    pass

                if process_finished:
                    break

                elapsed = time.time() - start_time
                if elapsed > timeout:
                    process.kill()
                    exit_code = -1
                    break

                time.sleep(0.01)

            # Join reader threads
            for t in threads:
                t.join(timeout=1)

            # Drain any remaining output
            try:
                while True:
                    stream_name, line = output_queue.get_nowait()
                    if stream_name in ("stdout", "stderr"):
                        if not displayed_any_output:
                            self.report_output("")
                            displayed_any_output = True
                        self.report_output(line)
            except queue.Empty:
                pass

            execution_time_ms = int((time.time() - start_time) * 1000)

            stdout_str = "".join(captured_stdout)
            stderr_str = "".join(captured_stderr)
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

            if success:
                summary = f"Completed in {execution_time_ms}ms"
                if stdout_str:
                    n_lines = len(stdout_str.strip().split("\n"))
                    summary += f" ({n_lines} lines output)"
                self.report_result(summary)
            else:
                error_msg = f"Exit code {exit_code}"
                if stderr_str:
                    stderr_preview = stderr_str[:200].replace("\n", " ")
                    if len(stderr_str) > 200:
                        stderr_preview += "..."
                    error_msg += f": {stderr_preview}"
                self.report_error(error_msg)
                result["error"] = f"gh exited with code {exit_code}"

            return result

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
            print(f"  Execution time: {result['execution_time_ms']}ms")
            if args.verbose:
                print(f"  Executable: {result.get('gh_executable', 'unknown')}")
                print(f"  Command: {result['command']}")
            if result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])
            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])
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

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
