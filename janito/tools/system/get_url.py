#!/usr/bin/env python3
"""
Get URL Tool - A class-based tool for fetching web content from URLs.

This tool demonstrates how to use the base tool class with progress reporting
for web requests.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.get_url [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import atexit
import json
import os
import sys
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool

# Threshold (in characters) above which fetched content is written to a
# temporary file instead of being returned inline to the model. Returning very
# large payloads tends to blow up the model context / JSON result, so we store
# them on disk and hand back a pointer instead.
BIG_CONTENT_THRESHOLD = 10_000

# Temporary files created by GetUrl for oversized content. They are removed
# automatically when the janito process exits.
_TEMP_FILES: set[str] = set()
_atexit_registered = False


def _cleanup_temp_files() -> None:
    """Remove all temporary files created by GetUrl (called on process exit)."""
    for path in list(_TEMP_FILES):
        try:
            os.remove(path)
        except OSError:
            pass
        _TEMP_FILES.discard(path)


def _track_temp_file(path: str) -> None:
    """Register a temporary file for removal on process exit."""
    global _atexit_registered
    if not path:
        return
    _TEMP_FILES.add(path)
    if not _atexit_registered:
        atexit.register(_cleanup_temp_files)
        _atexit_registered = True


@tool(permissions="r")
class GetUrl(BaseTool):
    """
    Tool for fetching content from web URLs.

    This tool retrieves content from HTTP/HTTPS URLs and returns the response.
    It supports various options for controlling the request behavior.
    """

    def run(
        self,
        url: str,
        max_length: int | None = 5000,
        max_lines: int | None = 200,
        timeout: int | None = 10,
        follow_redirects: bool = True,
        threshold: int | None = BIG_CONTENT_THRESHOLD,
    ) -> dict[str, Any]:
        """
        Fetch content from a URL and return results.

        Args:
            url (str): The URL to fetch content from (must be http:// or https://)
            max_length (Optional[int]): Maximum number of characters to return (default: 5000)
            max_lines (Optional[int]): Maximum number of lines to return (default: 200)
            timeout (Optional[int]): Request timeout in seconds (default: 10)
            follow_redirects (bool): Whether to follow HTTP redirects (default: True)
            threshold (Optional[int]): Content size (in characters) above which the
                full content is written to a temporary file instead of being returned
                inline. Pass None to disable. (default: 10000)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if request succeeded
                - 'content': fetched content as string (if successful and not too big)
                - 'message': message returned when content was too big and stored to a file
                - 'tmp_filename': path to the temporary file (only when content was too big)
                - 'too_big': bool (only present when content was stored to a temp file)
                - 'url': the URL that was fetched
                - 'status_code': HTTP status code (if available)
                - 'content_length': length of content in bytes
                - 'lines_returned': number of lines in returned content
                - 'error': error message if request failed (only present if success=False)
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                self.report_error("URL must start with http:// or https://")
                return {
                    "success": False,
                    "error": "URL must start with http:// or https://",
                    "url": url,
                }

            self.report_start(f"🌐 Fetching URL: {url}")

            # Build the fetch command using Python's urllib or requests equivalent
            # Since we need to use subprocess to match the existing pattern, we'll create a Python script
            fetch_script = f"""
import urllib.request
import urllib.error
import sys
import json
import tempfile

url = "{url}"
max_length = {max_length if max_length is not None else "None"}
max_lines = {max_lines if max_lines is not None else "None"}
timeout_val = {timeout if timeout is not None else "None"}
follow_redirects = {follow_redirects!r}
threshold = {threshold if threshold is not None else "None"}

try:
    # Create request with custom headers
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (compatible; AI-Tool/1.0)')

    # Handle redirects
    if not follow_redirects:
        # Create custom opener that doesn't handle redirects
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        response = opener.open(req, timeout=timeout_val)
    else:
        response = urllib.request.urlopen(req, timeout=timeout_val)

    # Read content
    content = response.read().decode('utf-8')
    status_code = response.getcode()
    content_length = len(content.encode('utf-8'))

    # If the full content is too big, store it in a temporary file instead of
    # returning it inline (which would blow up the model context). The temp
    # file is created with delete=False so it survives this subprocess; the
    # parent process registers it for cleanup on exit.
    if threshold is not None and len(content) > threshold:
        tmp = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            prefix='janito_geturl_',
            encoding='utf-8',
            delete=False,
        )
        tmp.write(content)
        tmp.close()

        result = {{
            "success": True,
            "too_big": True,
            "tmp_filename": tmp.name,
            "content_length": content_length,
            "lines_returned": content.count('\\n') + (1 if content and not content.endswith('\\n') else 0),
            "url": url,
            "status_code": status_code,
        }}
        print(json.dumps(result))
        sys.exit(0)

    # Apply limits
    if max_length is not None and len(content) > max_length:
        content = content[:max_length] + "... [truncated]"

    if max_lines is not None:
        lines = content.split('\\n')
        if len(lines) > max_lines:
            content = '\\n'.join(lines[:max_lines]) + "\\n... [truncated]"

    result = {{
        "success": True,
        "content": content,
        "url": url,
        "status_code": status_code,
        "content_length": content_length,
        "lines_returned": len(content.split('\\n'))
    }}

    print(json.dumps(result))

except urllib.error.HTTPError as e:
    result = {{
        "success": False,
        "error": f"HTTP Error {{e.code}}: {{e.reason}}",
        "url": url,
        "status_code": e.code
    }}
    print(json.dumps(result))

except urllib.error.URLError as e:
    result = {{
        "success": False,
        "error": f"URL Error: {{e.reason}}",
        "url": url
    }}
    print(json.dumps(result))

except Exception as e:
    result = {{
        "success": False,
        "error": f"Unexpected error: {{str(e)}}",
        "url": url
    }}
    print(json.dumps(result))
"""

            # Execute the fetch script using Python
            import subprocess
            import time

            start_time = time.time()

            process = subprocess.run(
                [sys.executable, "-c", fetch_script],
                capture_output=True,
                text=True,
                timeout=timeout + 5
                if timeout
                else 65,  # Add buffer for script overhead
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if process.returncode == 0:
                try:
                    result = json.loads(process.stdout)
                    if result["success"]:
                        # If the content was too big, it has been stored to a
                        # temporary file. Register the file for cleanup on exit,
                        # warn the user, and return a pointer message instead of
                        # the (huge) content.
                        if result.get("too_big") and result.get("tmp_filename"):
                            tmp_filename = result["tmp_filename"]
                            _track_temp_file(tmp_filename)

                            message = f"Content was too big, stored at {tmp_filename}"
                            self.report_warning(message)

                            return {
                                "success": True,
                                "message": message,
                                "too_big": True,
                                "tmp_filename": tmp_filename,
                                "url": url,
                                "status_code": result.get("status_code"),
                                "content_length": result.get("content_length"),
                                "lines_returned": result.get("lines_returned"),
                                "execution_time_ms": execution_time_ms,
                            }

                        # Report success
                        self.report_result(
                            f"Fetched {result['content_length']} bytes ({result['lines_returned']} lines)"
                        )

                        # Add execution time to result
                        result["execution_time_ms"] = execution_time_ms

                        return result
                    else:
                        self.report_error(result["error"])
                        result["execution_time_ms"] = execution_time_ms
                        return result
                except json.JSONDecodeError:
                    self.report_error("Failed to parse response")
                    return {
                        "success": False,
                        "error": "Failed to parse response from fetch script",
                        "url": url,
                        "execution_time_ms": execution_time_ms,
                        "raw_output": process.stdout[:200]
                        if process.stdout
                        else "No output",
                    }
            else:
                # Process failed
                error_msg = (
                    process.stderr.strip() if process.stderr else "Unknown error"
                )
                self.report_error(f"Fetch failed: {error_msg[:100]}")
                return {
                    "success": False,
                    "error": f"Fetch script failed: {error_msg}",
                    "url": url,
                    "execution_time_ms": execution_time_ms,
                }

        except subprocess.TimeoutExpired:
            self.report_error("Request timeout")
            return {
                "success": False,
                "error": f"URL fetch timed out after {timeout} seconds",
                "url": url,
            }
        except Exception as e:
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Failed to fetch URL: {e!s}",
                "url": url,
            }


# CLI interface for testing
def main():
    """Command line interface for testing the GetUrl tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch content from URLs for AI function calling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://httpbin.org/get"
  %(prog)s "https://example.com" --max-length 1000 --max-lines 50
  %(prog)s "https://api.github.com/users/octocat" --json
        """,
    )

    parser.add_argument("url", help="URL to fetch (must be http:// or https://)")
    parser.add_argument(
        "--max-length",
        "-l",
        type=int,
        default=5000,
        help="Maximum characters to return (default: 5000)",
    )
    parser.add_argument(
        "--max-lines",
        "-n",
        type=int,
        default=200,
        help="Maximum lines to return (default: 200)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
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
        "--no-follow-redirects", action="store_true", help="Don't follow HTTP redirects"
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output"
    )

    args = parser.parse_args()

    # Create tool instance and execute
    tool_instance = GetUrl()
    result = tool_instance.run(
        url=args.url,
        max_length=args.max_length,
        max_lines=args.max_lines,
        timeout=args.timeout,
        follow_redirects=not args.no_follow_redirects,
        threshold=None
        if args.threshold is not None and args.threshold < 0
        else args.threshold,
    )

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            # Oversized content was stored to a temporary file.
            if result.get("too_big"):
                print("? Content too big - stored to a temporary file")
                print(f"  URL: {result['url']}")
                print(f"  Status: {result.get('status_code', 'N/A')}")
                print(f"  Content length: {result.get('content_length', 'N/A')} bytes")
                print(f"  Lines: {result.get('lines_returned', 'N/A')}")
                print(f"  Temp file: {result.get('tmp_filename', 'N/A')}")
                print(f"  Execution time: {result.get('execution_time_ms', 'N/A')}ms")
                print(f"\n  {result.get('message', '')}")
                return 0

            print("? URL fetch successful")
            print(f"  URL: {result['url']}")
            print(f"  Status: {result.get('status_code', 'N/A')}")
            print(f"  Content length: {result.get('content_length', 'N/A')} bytes")
            print(f"  Lines returned: {result.get('lines_returned', 'N/A')}")
            print(f"  Execution time: {result.get('execution_time_ms', 'N/A')}ms")

            if args.verbose:
                print("\nContent:")
                print("-" * 40)
                print(result["content"])
            else:
                # Show truncated preview
                content_preview = result["content"][:200].replace("\n", " ")
                if len(result["content"]) > 200:
                    content_preview += "..."
                print(f"\nContent preview: {content_preview}")
        else:
            print("? URL fetch failed")
            print(f"  URL: {result['url']}")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            if "status_code" in result:
                print(f"  Status code: {result['status_code']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
