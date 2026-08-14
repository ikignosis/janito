#!/usr/bin/env python3
"""
Headless Browse Tool - Renders a URL with headless Google Chrome and returns
the page's DOM content.

Unlike GetUrl (a plain HTTP fetch), this tool drives a real browser engine, so
it sees content that is generated or modified by JavaScript after the initial
page load. It is only loaded when a Google Chrome (or Chromium-based) binary is
found on the system (see ``should_load``).

For direct execution, use: python -m janito.tools.net.headless_browse [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

from ...tooling import BaseTool, format_duration_ms
from ...tooling.decorator import tool
from ._chrome_utils import (
    BIG_CONTENT_THRESHOLD,
    _find_chrome,
    _track_temp_file,
    _truncate_content,
)


@tool(permissions="r")
class HeadlessBrowse(BaseTool):
    """
    Tool for rendering a URL with headless Google Chrome and returning the page content.

    Starts a headless Chrome instance, browses to the given URL, and returns the
    serialised DOM. Unlike GetUrl (a plain HTTP fetch), this renders JavaScript,
    so it captures content that only appears after the page executes its scripts.

    Only loaded when a Google Chrome (or Chromium-based) binary is found on the
    system. If it is missing, the tool is not advertised to the model.

    Args:
        url (str): The URL to browse (must be http:// or https://). Required.
        max_length (int): Maximum number of characters to return (default: 10000).
        max_lines (int): Maximum number of lines to return (default: 500).
        timeout (int): Chrome process timeout in seconds (default: 30).
        wait_ms (int): Virtual time budget in milliseconds to let JavaScript run
            before dumping the DOM (default: 1000).
        threshold (int): Content size (in characters) above which the full DOM is
            written to a temporary file instead of being returned inline. Pass
            None to disable. (default: 10000).
    """

    # Cached binary path, populated by should_load() during discovery. Also
    # resolved lazily inside run() so direct instantiation still works.
    _chrome_binary: str | None = None

    @classmethod
    def should_load(cls) -> bool:
        """Only load when a Google Chrome (or Chromium-based) binary is found."""
        chrome = _find_chrome()
        if chrome is None:
            cls._load_skip_reason = (
                "Google Chrome (or another Chromium-based browser) was not found "
                "on this system. Install Google Chrome to enable headless browsing."
            )
            return False
        cls._chrome_binary = chrome
        return True

    def run(
        self,
        url: str,
        max_length: int | None = 10_000,
        max_lines: int | None = 500,
        timeout: int | None = 30,
        wait_ms: int | None = 1_000,
        threshold: int | None = BIG_CONTENT_THRESHOLD,
    ) -> dict[str, Any]:
        """
        Browse to a URL with headless Chrome and return the rendered page content.

        Args:
            url (str): The URL to browse (must be http:// or https://).
            max_length (Optional[int]): Maximum number of characters to return
                (default: 10000).
            max_lines (Optional[int]): Maximum number of lines to return
                (default: 500).
            timeout (Optional[int]): Chrome process timeout in seconds
                (default: 30).
            wait_ms (Optional[int]): Virtual time budget in milliseconds to let
                JavaScript run before dumping the DOM (default: 1000).
            threshold (Optional[int]): Content size (in characters) above which
                the full DOM is written to a temporary file instead of being
                returned inline. Pass None to disable. (default: 10000).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if the page was rendered
                - 'content': rendered DOM as string (if successful and not too big)
                - 'message': message returned when content was too big and stored to a file
                - 'tmp_filename': path to the temporary file (only when content was too big)
                - 'too_big': bool (only present when content was stored to a temp file)
                - 'url': the URL that was browsed
                - 'chrome': path to the browser binary that was used
                - 'headless_mode': the headless flag that was used ("new" or "legacy")
                - 'exit_code': the Chrome process exit code
                - 'content_length': length of the rendered content in characters
                - 'lines_returned': number of lines in returned content
                - 'execution_time_ms': rendering duration in milliseconds
                - 'error': error message (only present if success is False)
        """
        try:
            # Validate URL.
            if not url.startswith(("http://", "https://")):
                self.report_error("URL must start with http:// or https://")
                return {
                    "success": False,
                    "error": "URL must start with http:// or https://",
                    "url": url,
                }

            # Resolve the browser binary (cached by should_load when discovered).
            chrome = getattr(type(self), "_chrome_binary", None) or _find_chrome()
            if not chrome:
                self.report_error("No Google Chrome (or Chromium-based) browser found")
                return {
                    "success": False,
                    "error": (
                        "No Google Chrome (or Chromium-based) browser found on this "
                        "system. Install Google Chrome to use headless browsing."
                    ),
                    "url": url,
                }

            self.report_start(f"🌐 Browsing {url} with headless Chrome", end="")

            start_time = time.time()

            # Isolated profile: avoids clashing with a running Chrome instance
            # and keeps this session's cookies/history out of the real profile.
            profile_dir = tempfile.mkdtemp(prefix="janito_chrome_")
            try:
                args = [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--user-data-dir={profile_dir}",
                    f"--virtual-time-budget={int(wait_ms or 0)}",
                    "--dump-dom",
                    url,
                ]
                # --no-sandbox is only required in root/container environments
                # (Chrome refuses to run as root with the sandbox enabled).
                if os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0:
                    args.insert(1, "--no-sandbox")

                headless_mode = "new"
                try:
                    proc = subprocess.run(
                        args,
                        capture_output=True,
                        timeout=timeout,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    self.report_error(
                        f"Chrome timed out after {timeout}s ({format_duration_ms(execution_time_ms)})"
                    )
                    return {
                        "success": False,
                        "error": f"Chrome timed out after {timeout}s",
                        "url": url,
                        "chrome": chrome,
                        "execution_time_ms": execution_time_ms,
                    }

                # Older Chromium builds reject "--headless=new"; fall back to the
                # legacy flag rather than failing outright.
                if proc.returncode != 0 and b"unknown command line flag" in (
                    proc.stderr or b""
                ):
                    args[args.index("--headless=new")] = "--headless"
                    headless_mode = "legacy"
                    try:
                        proc = subprocess.run(
                            args,
                            capture_output=True,
                            timeout=timeout,
                            check=False,
                        )
                    except subprocess.TimeoutExpired:
                        execution_time_ms = int((time.time() - start_time) * 1000)
                        self.report_error(
                            f"Chrome timed out after {timeout}s ({format_duration_ms(execution_time_ms)})"
                        )
                        return {
                            "success": False,
                            "error": f"Chrome timed out after {timeout}s",
                            "url": url,
                            "chrome": chrome,
                            "execution_time_ms": execution_time_ms,
                        }

                if proc.returncode != 0:
                    stderr_tail = (
                        (proc.stderr or b"").decode("utf-8", errors="replace").strip()
                    )
                    detail = (
                        stderr_tail[-500:]
                        if stderr_tail
                        else f"exit code {proc.returncode}"
                    )
                    self.report_error(f"Chrome failed ({detail})")
                    return {
                        "success": False,
                        "error": f"Chrome exited with an error: {detail}",
                        "url": url,
                        "chrome": chrome,
                        "exit_code": proc.returncode,
                    }

                content = proc.stdout.decode("utf-8", errors="replace")
                content_length = len(content)
                total_lines = content.count("\n") + (
                    1 if content and not content.endswith("\n") else 0
                )
                execution_time_ms = int((time.time() - start_time) * 1000)

                # If the rendered DOM is too big, store it in a temporary file
                # instead of returning it inline (would blow up the model context).
                if threshold is not None and len(content) > threshold:
                    tmp = tempfile.NamedTemporaryFile(
                        mode="w",
                        suffix=".html",
                        prefix="janito_browse_",
                        encoding="utf-8",
                        delete=False,
                    )
                    tmp.write(content)
                    tmp.close()

                    _track_temp_file(tmp.name)

                    message = f"Rendered page was too big, stored at {tmp.name}, use search methods to explore it."
                    self.report_warning(message)

                    return {
                        "success": True,
                        "message": message,
                        "too_big": True,
                        "tmp_filename": tmp.name,
                        "url": url,
                        "chrome": chrome,
                        "headless_mode": headless_mode,
                        "exit_code": proc.returncode,
                        "content_length": content_length,
                        "lines_returned": total_lines,
                        "execution_time_ms": execution_time_ms,
                    }

                content = _truncate_content(content, max_length, max_lines)
                lines_returned = len(content.split("\n"))

                self.report_result(
                    f"Fetched {content_length} chars ({lines_returned} lines) ({format_duration_ms(execution_time_ms)})"
                )

                return {
                    "success": True,
                    "content": content,
                    "url": url,
                    "chrome": chrome,
                    "headless_mode": headless_mode,
                    "exit_code": proc.returncode,
                    "content_length": content_length,
                    "lines_returned": lines_returned,
                    "execution_time_ms": execution_time_ms,
                }

            finally:
                shutil.rmtree(profile_dir, ignore_errors=True)

        except Exception as e:
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to browse URL: {e!s}",
                "url": url,
            }


# ── CLI testing harness ─────────────────────────────────────────────────────
def main():
    """Command line interface for testing the HeadlessBrowse."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Render a URL with headless Google Chrome and print the DOM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://example.com"
  %(prog)s "https://example.com" --max-length 2000 --max-lines 50
  %(prog)s "https://example.com" --wait-ms 3000 --json
        """,
    )

    parser.add_argument("url", help="URL to browse (must be http:// or https://)")
    parser.add_argument(
        "--max-length",
        "-l",
        type=int,
        default=10_000,
        help="Maximum characters to return (default: 10000)",
    )
    parser.add_argument(
        "--max-lines",
        "-n",
        type=int,
        default=500,
        help="Maximum lines to return (default: 500)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="Chrome process timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1_000,
        help="Virtual time budget in ms for JavaScript (default: 1000)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=BIG_CONTENT_THRESHOLD,
        help=(
            "Content size (chars) above which content is stored to a temp file "
            f"instead of returned inline (default: {BIG_CONTENT_THRESHOLD}, "
            "pass -1 to disable)"
        ),
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )
    args = parser.parse_args()

    result = HeadlessBrowse().run(
        url=args.url,
        max_length=args.max_length,
        max_lines=args.max_lines,
        timeout=args.timeout,
        wait_ms=args.wait_ms,
        threshold=None
        if args.threshold is not None and args.threshold < 0
        else args.threshold,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            if result.get("too_big"):
                print("? Rendered page too big - stored to a temporary file")
                print(f"  URL: {result['url']}")
                print(f"  Chrome: {result.get('chrome', 'N/A')}")
                print(f"  Content length: {result.get('content_length', 'N/A')} chars")
                print(f"  Temp file: {result.get('tmp_filename', 'N/A')}")
                print(
                    f"  Execution time: {format_duration_ms(result.get('execution_time_ms', 'N/A'))}"
                )
                print(f"\n  {result.get('message', '')}")
                return 0

            print("? Page rendered successfully")
            print(f"  URL: {result['url']}")
            print(f"  Chrome: {result.get('chrome', 'N/A')}")
            print(f"  Content length: {result.get('content_length', 'N/A')} chars")
            print(f"  Lines returned: {result.get('lines_returned', 'N/A')}")
            print(
                f"  Execution time: {format_duration_ms(result.get('execution_time_ms', 'N/A'))}"
            )

            if args.verbose:
                print("\nContent:")
                print("-" * 40)
                print(result["content"])
            else:
                content_preview = result["content"][:200].replace("\n", " ")
                if len(result["content"]) > 200:
                    content_preview += "..."
                print(f"\nContent preview: {content_preview}")
        else:
            print("? Page rendering failed")
            print(f"  URL: {result['url']}")
            print(f"  Error: {result.get('error', 'Unknown error')}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
